"""Normalizacion conservadora de horarios de equipos observados en FBM."""
from __future__ import annotations


class TeamScheduleError(ValueError):
    """La respuesta de horarios no tiene la forma requerida."""


def normalize_team_schedule(response: object) -> dict:
    """Mantiene valores oficiales sin deducir marcadores ni estados."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamScheduleError("Respuesta de horarios ambigua o con error")
    matches, current_round = response.get("partidos"), response.get("jornadaActual")
    if not isinstance(matches, list) or type(current_round) is not int:
        raise TeamScheduleError("Faltan partidos o jornada actual")
    required = {"IdPartido": "id", "NombreEquipoLocal": "local", "NombreEquipoVisitante": "visitante"}
    optional = {"Fecha": "fecha", "Hora": "hora", "FechaHoraUTC": "fecha_hora_utc",
                "CampoJuego": "campo", "DireccionCampo": "direccion", "Estado": "estado_oficial"}
    normalized = []
    for item in matches:
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip() for k in required):
            raise TeamScheduleError("Partido sin identificador o nombres")
        record = {out: item[name] for name, out in required.items()}
        for name, out in optional.items():
            value = item.get(name)
            if value is not None and not isinstance(value, str):
                raise TeamScheduleError("Campo de partido inesperado")
            record[out] = value
        number = item.get("NumeroJornada")
        if number is not None and type(number) is not int:
            raise TeamScheduleError("Numero de jornada no valido")
        record["jornada"] = number
        # Resultados y Estado no se interpretan como marcador ni estado en directo.
        normalized.append(record)
    return {"jornada_actual": current_round, "partidos": normalized}
