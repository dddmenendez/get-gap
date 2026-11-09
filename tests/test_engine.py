from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from get_gap.engine import SearchParams, find_slots, iter_candidates
from get_gap.models import BusyInterval, Member
from get_gap.plans import get_plan

MAD = ZoneInfo("Europe/Madrid")
# 1-7 de marzo de 2027: lunes a domingo
MON, SUN = date(2027, 3, 1), date(2027, 3, 7)


def dt(day: int, h: int, m: int = 0, month: int = 3) -> datetime:
    return datetime(2027, month, day, h, m, tzinfo=MAD)


def busy(start: datetime, end: datetime) -> BusyInterval:
    return BusyInterval(start=start, end=end)


def week(**kw) -> SearchParams:
    return SearchParams(date_from=MON, date_to=SUN, **kw)


@pytest.fixture
def trio() -> list[Member]:
    return [Member(name="Ana"), Member(name="Luis"), Member(name="Marta")]


def test_cena_sin_agenda_prefiere_jueves_a_sabado_a_las_21(trio):
    res = find_slots(get_plan("cena"), trio, week())
    assert [s.start for s in res] == [dt(4, 21), dt(5, 21), dt(6, 21)]
    assert all(s.all_in for s in res)
    assert res[0].end == dt(4, 23, 30)


def test_un_ocupado_saca_ese_dia_de_las_opciones_de_todos(trio):
    trio[0].busy = [busy(dt(5, 20), dt(5, 23, 59))]  # Ana, viernes por la noche
    res = find_slots(get_plan("cena"), trio, week())
    assert [s.start.date() for s in res] == [date(2027, 3, 4), date(2027, 3, 6), date(2027, 3, 1)]
    assert all(s.all_in for s in res)


def test_hora_se_desplaza_si_hay_conflicto_parcial(trio):
    trio[1].busy = [busy(dt(4, 20), dt(4, 21, 30))]  # Luis llega tarde el jueves
    res = find_slots(get_plan("cena"), trio, week())
    # Viernes a las 21:00 gana, pero el jueves sigue siendo opción a las 21:30
    assert res[0].start == dt(5, 21)
    assert dt(4, 21, 30) in [s.start for s in res]


def test_si_nadie_cuadra_propone_con_minimo_de_asistentes(trio):
    every_night = [busy(dt(d, 20), dt(d, 23, 59)) for d in range(1, 8)]
    trio[2].busy = every_night  # Marta no puede ninguna noche
    assert find_slots(get_plan("cena"), trio, week()) == []
    res = find_slots(get_plan("cena"), trio, week(min_attendees=2))
    assert len(res) == 3
    assert all(s.unavailable == ["Marta"] for s in res)


def test_prefiere_mas_asistentes_antes_que_dia_preferido(trio):
    # Thu-Sat solo pueden 2; martes pueden los 3
    for d in (4, 5, 6):
        trio[0].busy.append(busy(dt(d, 19), dt(d, 23, 59)))
    for d in (1, 3, 7):
        trio[1].busy.append(busy(dt(d, 19), dt(d, 23, 59)))
    res = find_slots(get_plan("cena"), trio, week(min_attendees=2))
    assert res[0].start.date() == date(2027, 3, 2)
    assert res[0].all_in
    assert not res[1].all_in


def test_required_obliga_a_que_vaya_esa_persona(trio):
    trio[0].busy = [busy(dt(4, 0), dt(6, 23, 59))]  # Ana fuera jue-sáb
    res = find_slots(
        get_plan("cena"), trio, week(min_attendees=1, required=frozenset({trio[0].id}))
    )
    assert all("Ana" in s.available for s in res)
    assert {s.start.weekday() for s in res}.isdisjoint({3, 4, 5})


def test_nunca_dos_opciones_el_mismo_dia(trio):
    res = find_slots(get_plan("cafe"), trio, week(limit=7))
    days = [s.start.date() for s in res]
    assert len(days) == len(set(days)) == 7


def test_viaje_es_viernes_a_domingo_y_un_hueco_el_sabado_lo_rompe(trio):
    params = SearchParams(date_from=MON, date_to=date(2027, 3, 21))
    trio[1].busy = [busy(dt(6, 12), dt(6, 14))]  # Luis tiene algo el sábado 6
    res = find_slots(get_plan("viaje"), trio, params)
    assert [s.start for s in res] == [dt(12, 15), dt(19, 15)]
    assert res[0].end == dt(14, 22)


def test_busy_en_utc_se_compara_bien_con_madrid(trio):
    # 20:00 UTC = 21:00 en Madrid (CET, marzo antes del cambio de hora)
    utc = timezone.utc
    trio[0].busy = [
        BusyInterval(
            start=datetime(2027, 3, 4, 20, 0, tzinfo=utc),
            end=datetime(2027, 3, 4, 22, 0, tzinfo=utc),
        )
    ]
    res = find_slots(get_plan("cena"), trio, week(limit=1))
    assert res[0].start.date() != date(2027, 3, 4)


def test_not_before_descarta_huecos_pasados(trio):
    res = find_slots(get_plan("cena"), trio, week(not_before=dt(6, 0)))
    assert all(s.start >= dt(6, 0) for s in res)


def test_candidatos_respetan_franja():
    plan = get_plan("cena")
    cands = list(iter_candidates(plan, MON, MON, MAD))
    assert cands[0][0].time() == time(20, 30)
    assert cands[-1][1] == datetime(2027, 3, 2, 0, 0, tzinfo=MAD)


def test_duracion_personalizada_amplia_franja():
    plan = get_plan("viaje").with_duration(timedelta(days=3))
    assert plan.window_length >= plan.duration


def test_busy_sin_zona_horaria_falla():
    with pytest.raises(ValueError):
        BusyInterval(start=datetime(2027, 3, 1, 10), end=datetime(2027, 3, 1, 11))
