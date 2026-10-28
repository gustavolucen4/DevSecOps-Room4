#!/usr/bin/env bash
# Simulação CONTROLADA de força bruta contra a TaskFlow local (Módulo 6).
# Uso: scripts/simular-forca-bruta.sh [URL] [USUARIO] [TENTATIVAS]
# Só aponte para o ambiente do próprio grupo. Cada tentativa busca um token CSRF novo,
# como um atacante faria, e envia uma senha errada.
set -euo pipefail
TARGET="${1:-http://127.0.0.1:8080}"
USER_ALVO="${2:-admin}"
TENTATIVAS="${3:-40}"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

echo "Alvo: $TARGET/login | usuário: $USER_ALVO | tentativas: $TENTATIVAS"
for i in $(seq 1 "$TENTATIVAS"); do
  token="$(curl -s -c "$JAR" -b "$JAR" "$TARGET/login" \
    | sed -n 's/.*name="csrf_token" value="\([^"]*\)".*/\1/p' | head -n1)"
  code="$(curl -s -o /dev/null -w '%{http_code}' -c "$JAR" -b "$JAR" \
    -A "bruteforce-sim/1.0" \
    --data-urlencode "csrf_token=$token" \
    --data-urlencode "username=$USER_ALVO" \
    --data-urlencode "password=senha-errada-$i" \
    "$TARGET/login")"
  printf 'tentativa %02d -> HTTP %s\n' "$i" "$code"
  sleep 0.2
done
echo "Pronto. Abra o Grafana (http://127.0.0.1:3000) > TaskFlow - Segurança e Login."
