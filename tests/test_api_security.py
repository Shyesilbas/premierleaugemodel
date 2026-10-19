import os
from unittest import mock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api import security

app = FastAPI()


@app.post("/admin", dependencies=[Depends(security.require_admin_token)])
def admin():
    return {"ok": True}


client = TestClient(app)


def _env(**values):
    return mock.patch.dict(os.environ, values, clear=False)


def test_admin_route_is_open_without_a_configured_token_and_warns_once():
    with _env(PLM_ADMIN_TOKEN=""), mock.patch.object(security, "_warned_open", False), \
         mock.patch.object(security.logger, "warning") as warning:
        assert client.post("/admin").status_code == 200
        assert client.post("/admin").status_code == 200
    assert warning.call_count == 1


def test_admin_route_requires_the_exact_token_once_configured():
    with _env(PLM_ADMIN_TOKEN="s3cret-token"):
        assert client.post("/admin").status_code == 401
        assert client.post("/admin", headers={"X-Admin-Token": "wrong"}).status_code == 401
        assert client.post("/admin", headers={"X-Admin-Token": "s3cret"}).status_code == 401  # a prefix is not enough
        assert client.post("/admin", headers={"X-Admin-Token": "s3cret-token"}).status_code == 200


def test_cors_origins_default_to_local_dev_servers_and_follow_the_environment():
    with _env(PLM_CORS_ORIGINS=""):
        assert "*" not in security.cors_origins()
        assert "http://localhost:5173" in security.cors_origins()
    with _env(PLM_CORS_ORIGINS=" https://a.example , https://b.example ,"):
        assert security.cors_origins() == ["https://a.example", "https://b.example"]
