import json
import re
import secrets

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app, get_db, init_db

# Credencial efêmera dos testes; não é uma conta da aplicação.
TEST_PASSWORD = secrets.token_urlsafe(24)


@pytest.fixture
def app(tmp_path):
    # Cada teste tem um SQLite temporário e dois usuários para verificar isolamento.
    app = create_app({"TESTING": True, "SECRET_KEY": secrets.token_hex(32),
                      "DATABASE": str(tmp_path / "test.db"), "SESSION_COOKIE_SECURE": False})
    with app.app_context():
        init_db()
        db = get_db()
        for username in ("alice", "bob"):
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (username, generate_password_hash(TEST_PASSWORD)))
        db.execute("INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
                   (2, "private-bob-task", "confidential"))
        db.commit()
    return app


def token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def login(client, username="alice", password=None):
    return client.post("/login", data={"username": username, "password": password or TEST_PASSWORD,
                                       "csrf_token": token(client)})


def test_login_and_password_hash(app):
    client = app.test_client()
    assert login(client).status_code == 302
    assert client.get("/tasks").status_code == 200
    with app.app_context():
        password = get_db().execute("SELECT password FROM users WHERE username = ?",
                                    ("alice",)).fetchone()[0]
        assert password != TEST_PASSWORD
        assert check_password_hash(password, TEST_PASSWORD)


def test_sql_injection_does_not_authenticate(app):
    client = app.test_client()
    assert login(client, "' OR 1=1 --", "incorrect").status_code == 200
    assert client.get("/tasks").status_code == 302


def test_search_isolates_users(app):
    # Uma tentativa de SQLi não pode revelar a tarefa do outro usuário.
    client = app.test_client()
    login(client)
    response = client.get("/tasks", query_string={"q": "' OR 1=1 --"})
    assert response.status_code == 200
    assert b"private-bob-task" not in response.data
    assert b"private-bob-task" not in client.get("/tasks").data


def test_task_xss_escaped(app):
    # O conteúdo é salvo, mas deve voltar como texto escapado, sem executar HTML.
    client = app.test_client()
    login(client)
    result = client.post("/tasks/new", data={"csrf_token": token(client, "/tasks/new"),
                         "title": "<script>alert(1)</script>", "description": "<b>unsafe</b>"})
    assert result.status_code == 302
    html = client.get("/tasks").get_data(as_text=True)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in html


def test_csrf_required_and_debug_removed(app):
    client = app.test_client()
    assert client.post("/login", data={"username": "alice"}).status_code == 400
    assert client.get("/debug/info").status_code == 404
    assert app.debug is False


def test_csrf_flag_only_disables_when_explicit(monkeypatch, tmp_path, capsys):
    # TASKFLOW_CSRF=0 é só para o DAST: sem a variável, a proteção continua ligada.
    monkeypatch.setenv("TASKFLOW_SECRET_KEY", secrets.token_hex(32))
    monkeypatch.delenv("TASKFLOW_CSRF", raising=False)
    assert create_app().config["WTF_CSRF_ENABLED"] is True
    monkeypatch.setenv("TASKFLOW_CSRF", "0")
    scan_app = create_app({"DATABASE": str(tmp_path / "scan.db")})
    assert scan_app.config["WTF_CSRF_ENABLED"] is False
    assert "csrf_disabled" in capsys.readouterr().out
    # O formulário continua com o campo do token, então a regra 10202 do ZAP segue válida.
    with scan_app.app_context():
        init_db()
    assert 'name="csrf_token"' in scan_app.test_client().get("/login").get_data(as_text=True)


def test_missing_secret_fails(monkeypatch):
    monkeypatch.delenv("TASKFLOW_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app()


def test_login_error_and_search_escape_xss(app):
    # Sinks adicionais do Encontro 9: mensagem de erro do login e parâmetro q da busca.
    client = app.test_client()
    payload = "<script>alert(1)</script>"
    html = login(client, payload, "incorrect").get_data(as_text=True)
    assert payload not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    login(client)
    html = client.get("/tasks", query_string={"q": payload}).get_data(as_text=True)
    assert payload not in html
    assert "Resultados para: &lt;script&gt;" in html


def test_debug_off_by_default_and_security_headers(app, monkeypatch):
    monkeypatch.delenv("TASKFLOW_DEBUG", raising=False)
    response = app.test_client().get("/login")
    assert app.debug is False
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]


def test_logs_are_json_without_secrets(app, capsys):
    client = app.test_client()
    login(client, "alice", "senha-errada-123")
    login(client)
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    events = {entry["event"] for entry in lines}
    assert {"login_failed", "login_success", "http_request"} <= events
    assert all(entry.get("request_id") for entry in lines)
    raw = json.dumps(lines)
    assert "senha-errada-123" not in raw
    assert TEST_PASSWORD not in raw
    assert "csrf_token" not in raw
