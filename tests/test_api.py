from fastapi.testclient import TestClient

from get_gap.main import app, store

client = TestClient(app)


def setup_function():
    store.clear()


def test_flujo_completo_cena():
    g = client.post("/groups", json={"name": "Los de siempre"}).json()
    ids = {
        name: client.post(f"/groups/{g['id']}/members", json={"name": name}).json()["id"]
        for name in ("Ana", "Luis", "Marta")
    }
    r = client.put(
        f"/groups/{g['id']}/members/{ids['Ana']}/busy",
        json=[{"start": "2027-03-05T20:00:00+01:00", "end": "2027-03-05T23:59:00+01:00"}],
    )
    assert r.status_code == 200

    r = client.post(
        f"/groups/{g['id']}/suggest",
        json={"plan": "cena", "date_from": "2027-03-01", "date_to": "2027-03-07"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["suggestions"]) == 3
    assert body["suggestions"][0]["start"].startswith("2027-03-04T21:00")
    assert "jueves 4 de marzo, 21:00-23:30" in body["whatsapp_text"]
    assert "vamos todos" in body["whatsapp_text"]


def test_plan_desconocido_422():
    g = client.post("/groups", json={"name": "x"}).json()
    r = client.post(f"/groups/{g['id']}/suggest", json={"plan": "karaoke"})
    assert r.status_code == 422


def test_grupo_inexistente_404():
    assert client.post("/groups/nope/suggest", json={"plan": "cena"}).status_code == 404


def test_zona_horaria_invalida_422():
    assert client.post("/groups", json={"name": "x", "timezone": "Marte/Olympus"}).status_code == 422


def test_listar_planes():
    keys = {p["key"] for p in client.get("/plans").json()}
    assert {"cena", "viaje", "cafe"} <= keys


def test_texto_viaje_multidia():
    g = client.post("/groups", json={"name": "Viajeros"}).json()
    client.post(f"/groups/{g['id']}/members", json={"name": "Ana"})
    r = client.post(
        f"/groups/{g['id']}/suggest",
        json={"plan": "viaje", "date_from": "2027-03-01", "date_to": "2027-03-14", "limit": 1},
    ).json()
    assert r["whatsapp_text"].splitlines()[1].startswith("1. del viernes 5 de marzo (15:00) al domingo 7 (22:00)")
