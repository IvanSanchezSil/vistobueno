"""Tests del montaje de la SPA construida en la API."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from validator import api as api_module


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    return app


def test_monta_spa_con_index(tmp_path):
    (tmp_path / "index.html").write_text(
        "<!doctype html><div id='root'>VistoBueno</div>",
        encoding="utf-8",
    )
    app = _app()

    assert api_module._montar_spa(app, tmp_path) is True

    client = TestClient(app)
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "VistoBueno" in respuesta.text
    assert client.get("/api/ping").json() == {"ok": True}
    assert client.get("/docs").status_code == 200


def test_no_monta_spa_sin_index(tmp_path):
    app = _app()

    assert api_module._montar_spa(app, tmp_path) is False

    client = TestClient(app)
    assert client.get("/").status_code == 404
    assert client.get("/api/ping").json() == {"ok": True}


def test_app_real_sirve_spa_si_esta_construida():
    if not (api_module.FRONTEND_DIST / "index.html").is_file():
        pytest.skip("frontend/dist no está construido")

    client = TestClient(
        api_module.app,
        client=("127.0.0.1", 50000),
        base_url="http://127.0.0.1",
    )
    assert client.get("/").status_code == 200
