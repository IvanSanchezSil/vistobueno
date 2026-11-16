"""Contraejemplos locales de la API. No abre puertos ni envía solicitudes a UNT.

Ejecutar con el Python del proyecto. VISTOBUENO_AUDIT_ROOT permite otra copia
local de la misma base. Las aserciones describen el defecto de c9e5499; no se
deben copiar como comportamiento deseado a la suite de regresión.
"""

import json
from copy import deepcopy
from unittest.mock import patch
import os
import sys
from pathlib import Path

root = Path(os.environ.get("VISTOBUENO_AUDIT_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(root))
from fastapi.testclient import TestClient
from validator.api import app

client = TestClient(app, base_url="http://localhost", client=("127.0.0.1", 51000))
ficha = {
    "extraidos": [
        {"campo": "dc.title", "valor": ["Título como lista"]},
        {"campo": "dc.contributor.author", "valor": ["Autora ficticia A", "Autor ficticio B"]},
    ],
    "manuales": [{"campo": "renati.author.dni", "valor": ["", "22222222"]}],
}
response = client.post("/ficha-pendiente", json=ficha)
assert response.status_code == 201
results = {"ficha_con_titulo_lista_y_hueco_dni": response.status_code}
ficha["extraidos"][0]["valor"] = "Tesis ficticia A"
response = client.post("/ficha-pendiente", json=ficha)
assert response.status_code == 201
tramite_id = response.json()["tramite_id"]
for name, data in [
    ("titulo_ajeno", {"handle": "https://hdl.handle.net/20.500.14414/900001", "titulo_observado": "OTRA TESIS", "timestamp": "2026-11-16T10:00:00"}),
    ("uri_invalida", {"handle": "not-a-handle", "titulo_observado": "Tesis ficticia A", "timestamp": "2026-11-16T10:00:00"}),
    ("fecha_invalida", {"handle": "https://hdl.handle.net/20.500.14414/900001", "titulo_observado": "Tesis ficticia A", "timestamp": "not-a-date"}),
]:
    response = client.post("/deposito", json={"tramite_id": tramite_id, **data})
    assert response.status_code == 204
    results[name] = response.status_code
# Se simula una corrección externa a la ficha; no se ejecuta DSpace.
ficha_canonica = {
    "extraidos": [
        {"campo": "dc.title", "valor": "Tesis ficticia A"},
        {"campo": "dc.contributor.author", "valor": ["Autor original ficticio"]},
    ],
    "manuales": [{"campo": "matricula", "valor": ["11111111-11"]}],
}
def preparar(ficha_actual):
    published = client.post("/ficha-pendiente", json=ficha_actual)
    assert published.status_code == 201
    current_id = published.json()["tramite_id"]
    payload = {"tramite_id": current_id, "handle": "https://hdl.handle.net/20.500.14414/900001", "titulo_observado": "Tesis ficticia A", "timestamp": "2026-11-16T10:00:00"}
    assert client.post("/deposito", json=payload).status_code == 204
    return {"ficha": ficha_actual, "tramite_id": current_id, "handle": payload["handle"], "timestamp": payload["timestamp"]}

with patch.dict(os.environ, {"VISTOBUENO_FIRMA": "Responsable ficticio"}):
    request = preparar(ficha_canonica)
    response = client.post("/fila-registro", json=request)
    assert response.status_code == 200, response.text
    assert any("Autor original ficticio" in row for row in response.json()["filas"])
    changed = deepcopy(request)
    changed["ficha"]["extraidos"][1]["valor"] = ["Autor corregido ficticio"]
    rejected = client.post("/fila-registro", json=changed)
    assert rejected.status_code == 409
    results["correccion_externa_no_reconciliada"] = {"papeleo_con_nombre_original": response.status_code, "sustitucion_de_ficha_rechazada_correctamente": rejected.status_code}
    malformed = deepcopy(ficha_canonica)
    malformed["manuales"][0]["valor"] = ["", "22222222-22"]
    response = client.post("/fila-registro", json=preparar(malformed))
    assert response.status_code == 200, response.text
    assert any("22222222-22" in row for row in response.json()["filas"])
    results["matricula_de_segunda_posicion_usada_para_un_autor"] = response.status_code
client.close()
Path(__file__).with_name("resultado_api.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results))
