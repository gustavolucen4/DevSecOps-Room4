"""TaskFlow com consultas parametrizadas, hashing, CSRF, headers de segurança e logs em JSON."""

import json
import logging
import os
import sqlite3
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import click
from flask import Flask, current_app, g, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

# Campos que nunca podem chegar ao log, mesmo que alguém os passe por engano.
SENSITIVE_KEYS = {"password", "senha", "token", "csrf_token", "cookie", "authorization",
                  "secret", "session"}


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por evento: o Promtail/Loki extraem os campos sem regex frágil."""

    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in getattr(record, "fields", {}).items():
            if key.lower() not in SENSITIVE_KEYS:
                entry[key] = value
        return json.dumps(entry, ensure_ascii=False)


class StdoutHandler(logging.StreamHandler):
    """Resolve sys.stdout a cada emissão (Gunicorn e pytest podem trocar o stream)."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):
        pass


def build_logger():
    logger = logging.getLogger("taskflow")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = JsonFormatter()
    stdout = StdoutHandler()
    stdout.setFormatter(formatter)
    logger.addHandler(stdout)
    # Arquivo opcional: o Promtail lê de um volume, sem precisar do docker.sock.
    log_file = os.environ.get("TASKFLOW_LOG_FILE")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


log = build_logger()


def log_event(event, level=logging.INFO, **fields):
    # request_id, IP, método e rota entram em todo evento da requisição.
    base = {"event": event}
    if request:
        base.update({
            "request_id": getattr(g, "request_id", None),
            "client_ip": request.remote_addr,
            "method": request.method,
            "path": request.path,
            "user_agent": request.headers.get("User-Agent", "")[:200],
        })
    base.update(fields)
    log.log(level, event, extra={"fields": base})


# Uma conexão por requisição evita compartilhar estado entre usuários.
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        # SQLite exige ativação explícita das relações entre usuários e tarefas.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


# Só cria a estrutura: não recria as contas com senhas públicas do exemplo.
def init_db():
    Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    get_db().executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT,
            done INTEGER DEFAULT 0
        );
    """)
    get_db().commit()


# A factory permite iniciar no Gunicorn e testar com um banco temporário isolado.
def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        # A chave assina a sessão; vem do ambiente e não fica no Git ou na imagem.
        SECRET_KEY=os.environ.get("TASKFLOW_SECRET_KEY"),
        DATABASE=os.environ.get("TASKFLOW_DATABASE", "instance/taskflow.db"),
        # HttpOnly restringe acesso por JavaScript; SameSite reduz envios entre sites.
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Secure exige HTTPS; o laboratório em localhost pode optar por HTTP.
        SESSION_COOKIE_SECURE=os.environ.get("TASKFLOW_HTTPS", "1") == "1",
        MAX_CONTENT_LENGTH=64 * 1024,
        # Debug só por variável explícita e desligado por padrão (Módulo 4).
        DEBUG=os.environ.get("TASKFLOW_DEBUG", "0") == "1",
        # Ligado por padrão. Só o container do DAST usa TASKFLOW_CSRF=0, para os payloads
        # do ZAP chegarem aos sinks em vez de pararem no 400 do CSRF (docs/dast.md).
        WTF_CSRF_ENABLED=os.environ.get("TASKFLOW_CSRF", "1") != "0",
    )
    if test_config:
        app.config.update(test_config)
    app.debug = bool(app.config["DEBUG"])
    # Falhar sem chave evita iniciar com uma chave previsível de fallback.
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Defina TASKFLOW_SECRET_KEY antes de iniciar.")
    # Fica visível no log (e no Loki) se alguém subir assim fora do scan.
    if not app.config["WTF_CSRF_ENABLED"]:
        log_event("csrf_disabled", logging.WARNING)
    # Atrás do proxy do Compose, o IP real vem do X-Forwarded-For de UM salto confiável.
    trusted_proxies = int(os.environ.get("TASKFLOW_TRUSTED_PROXIES", "0"))
    if trusted_proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=trusted_proxies, x_proto=trusted_proxies)
    @app.before_request
    def start_request():
        # Aceita um ID vindo do proxy (correlação ponta a ponta) só se tiver formato de UUID.
        incoming = request.headers.get("X-Request-ID", "")
        try:
            g.request_id = str(uuid.UUID(incoming))
        except ValueError:
            g.request_id = str(uuid.uuid4())
        g.started = time.perf_counter()

    # Registrado depois do request_id: até a rejeição por CSRF sai correlacionada no log.
    CSRFProtect(app)

    @app.after_request
    def security_headers(response):
        # Headers que o ZAP Baseline cobra (CSP, clickjacking, MIME sniffing, cache).
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        if request.path != "/healthz":
            log_event("http_request", status=response.status_code,
                      duration_ms=round((time.perf_counter() - g.get("started", time.perf_counter())) * 1000, 2))
        return response

    @app.teardown_appcontext
    def close_connection(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        click.echo("Banco inicializado; nenhum usuário padrão foi criado.")

    @app.cli.command("create-user")
    @click.argument("username")
    # Solicita e confirma a senha no terminal, sem exibi-la na tela.
    @click.password_option()
    def create_user(username, password):
        if len(password) < 12:
            raise click.ClickException("Use uma senha com pelo menos 12 caracteres.")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                # Guardamos o hash com salt, não a senha original.
                (username, generate_password_hash(password)),
            )
            db.commit()
        except sqlite3.IntegrityError as exc:
            raise click.ClickException("Usuário já existe.") from exc
        click.echo("Usuário criado.")

    @app.route("/healthz")
    def healthz():
        # Usado pelo HEALTHCHECK, pelo Compose e pela espera ativa do DAST.
        return {"status": "ok"}

    @app.route("/")
    def index():
        return redirect(url_for("tasks" if "user_id" in session else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        username = ""
        if request.method == "POST":
            username = request.form.get("username", "")[:100]
            # O placeholder ? separa a instrução SQL do valor informado pelo usuário.
            user = get_db().execute(
                "SELECT * FROM users WHERE username = ?", (username,),
            ).fetchone()
            # A biblioteca verifica a senha contra o hash armazenado.
            if user and check_password_hash(user["password"], request.form.get("password", "")):
                # Descarta o estado anterior antes de criar a sessão autenticada.
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                # Só o usuário: nunca request.form inteiro (levaria a senha ao Loki).
                log_event("login_success", username=username, user_id=user["id"])
                return redirect(url_for("tasks"))
            log_event("login_failed", logging.WARNING, username=username,
                      reason="unknown_user" if user is None else "bad_password")
            # Sink de XSS do Encontro 9: o usuário volta na mensagem, escapado pelo Jinja.
            error = f"Usuário {username} ou senha inválidos."
        return render_template("login.html", error=error, username=username)

    # Logout altera a sessão: usa POST e recebe proteção CSRF.
    @app.route("/logout", methods=["POST"])
    def logout():
        log_event("logout", user_id=session.get("user_id"))
        session.clear()
        return redirect(url_for("login"))

    @app.route("/tasks")
    def tasks():
        if "user_id" not in session:
            return redirect(url_for("login"))
        q = request.args.get("q", "")[:200]
        # O dono vem da sessão, não de um parâmetro controlado pelo navegador.
        rows = get_db().execute(
            "SELECT * FROM tasks WHERE user_id = ? AND title LIKE ?",
            (session["user_id"], "%" + q + "%"),
        ).fetchall()
        log_event("task_list", user_id=session["user_id"], count=len(rows), has_query=bool(q))
        # Templates .html do Jinja escapam título, descrição e q (sem | safe).
        return render_template("tasks.html", tasks=rows, q=q)

    @app.route("/tasks/new", methods=["GET", "POST"])
    def new_task():
        if "user_id" not in session:
            return redirect(url_for("login"))
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title or len(title) > 200:
                return "Título obrigatório, com até 200 caracteres.", 400
            db = get_db()
            # O INSERT também é parametrizado; a tarefa pertence à sessão atual.
            cursor = db.execute(
                "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
                (session["user_id"], title, request.form.get("description", "")),
            )
            db.commit()
            # Registramos o ID e o tamanho, não o conteúdo (pode ter dado pessoal).
            log_event("task_created", user_id=session["user_id"], task_id=cursor.lastrowid,
                      title_len=len(title))
            return redirect(url_for("tasks"))
        return render_template("new.html")

    # Não existe rota /debug/info: ela expunha variáveis de ambiente e configuração.
    return app
