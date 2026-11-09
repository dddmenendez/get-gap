# get-gap

Encuentra el hueco para la próxima quedada sin que nadie tenga que sacar el móvil.

Un grupo (p. ej. el de WhatsApp) elige un plan — cena, viaje, café… — y get-gap cruza
las agendas de todos los miembros y propone las mejores fechas, listas para pegar en el chat:

```
📅 Cena: opciones
1. jueves 4 de marzo, 21:00-23:30 · vamos todos ✅
2. sábado 6 de marzo, 21:00-23:30 · vamos todos ✅
3. viernes 5 de marzo, 21:00-23:30 · falta: Ana
```

## Cómo funciona

- **Solo libre/ocupado.** Nunca se leen títulos ni detalles de eventos.
- **Plantillas de plan** (`get_gap/plans.py`): cada tipo define franja horaria, duración,
  días posibles y preferidos.

  | Plan | Franja | Duración | Días |
  |---|---|---|---|
  | `cafe` | 09:00–21:00 | 1 h | todos |
  | `comida` | 13:30–17:00 | 2 h | todos (mejor finde) |
  | `cena` | 20:30–00:00 | 2 h 30 | todos (mejor jue–sáb) |
  | `deporte` | 08:00–22:00 | 1 h 30 | todos (mejor finde) |
  | `finde` | 10:00–20:00 | 10 h | sáb/dom |
  | `escapada` | sáb 10:00 → dom 20:00 | | sábado |
  | `viaje` | vie 15:00 → dom 22:00 | | viernes |

- **Ranking**: primero las fechas donde puede ir más gente; a igualdad, día preferido,
  hora más cercana a la ideal y fecha más próxima. Nunca dos opciones el mismo día.
- Opciones: `min_attendees` (si no cuadra para todos), `required` (quien tiene que ir sí o sí),
  `duration_hours` (p. ej. viaje de 4 días).

## Fuentes de calendario

| Fuente | Estado |
|---|---|
| Marcado manual | ✅ |
| Google Calendar (OAuth + freeBusy) | pendiente |
| iCloud (CalDAV + contraseña de aplicación) | pendiente |
| Atajo de iOS (envía solo ocupado) | futuro |

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
uvicorn get_gap.main:app --reload   # docs en http://127.0.0.1:8000/docs
```

### API

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/plans` | Lista los tipos de plan |
| POST | `/groups` | Crea un grupo |
| GET | `/groups/{id}` | Ver grupo |
| POST | `/groups/{id}/members` | Añade miembro |
| PUT | `/groups/{id}/members/{mid}/busy` | Marcado manual de ocupado |
| POST | `/groups/{id}/suggest` | Propone fechas para un plan |

```bash
curl -X POST localhost:8000/groups/$G/suggest \
  -H 'content-type: application/json' \
  -d '{"plan": "cena", "date_from": "2027-03-01", "date_to": "2027-03-31"}'
```
