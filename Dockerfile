# Versão e digest fixam a base; Alpine reduz a quantidade de pacotes do SO.
FROM python:3.12.13-alpine3.23@sha256:601d3d3797e90e2534782e69c85fafb7971b43f24c7b1b079b7e48dd435e458d
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASKFLOW_DATABASE=/app/data/taskflow.db
WORKDIR /app
# Atualiza correções do SO e cria identidade sem privilégios de root.
# Os pacotes do apk variam com o repositório: reconstruir e auditar regularmente.
RUN apk upgrade --no-cache && addgroup -g 10001 taskflow \
    && adduser -D -H -u 10001 -G taskflow taskflow \
    && mkdir /app/data /app/logs && chown taskflow:taskflow /app/data /app/logs
COPY requirements.txt .
# Hashes conferem a integridade dos pacotes; dependências transitivas são fixadas.
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt
# Copiamos apenas o produto; codigo/ contém exemplos vulneráveis da disciplina.
COPY --chown=taskflow:taskflow app.py .
COPY --chown=taskflow:taskflow templates/ templates/
# O processo da aplicação roda com UID/GID não-root.
USER 10001:10001
EXPOSE 5000
# Healthcheck sem curl: o wget do BusyBox já existe na base Alpine.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:5000/healthz || exit 1
# Gunicorn serve a aplicação; nenhuma senha ou chave é embutida na imagem.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
