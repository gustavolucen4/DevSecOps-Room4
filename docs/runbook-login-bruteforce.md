# Runbook — Resposta a Força Bruta no Login (NIST SP 800-61)

| Parâmetro | Definição |
|---|---|
| Serviço Alvo | TaskFlow (`POST /login`) |
| Severidade Inicial | MÉDIA (sobe para ALTA em caso de autenticação bem-sucedida pelo IP atacante) |
| Painel de Monitoramento | Grafana: `TaskFlow - Segurança e Login` |
| Responsável | SRE de plantão / Time de Desenvolvimento |

---

## Condição de Disparo

O alarme dispara quando houver mais de 10 falhas de autenticação originadas do mesmo IP em 5 minutos.

Consulta LogQL (Painel 2):
```logql
sum by (client_ip) (count_over_time({job="taskflow", event="login_failed"} | json [5m])) > 10
```

---

## 1. Preparação

- Logs estruturados em formato JSON com campos `ts`, `event`, `request_id`, `client_ip` e `username`.
- Descarte obrigatório de campos sensíveis (`password`, `token`, `csrf_token`) no formatador de logs.
- Stack de monitoramento ativa (Grafana, Loki, Promtail) via Docker Compose.
- Script para testes e simulação disponível em `scripts/simular-forca-bruta.sh`.

---

## 2. Detecção e Análise

### 2.1 Identificar o IP Atacante
Consultar o Painel 2 do Grafana ou executar a query de disparo no Explore para obter o `client_ip`.

### 2.2 Identificar Usuários Alvo
```logql
topk(5, sum by (username) (count_over_time({job="taskflow", event="login_failed"} | json | client_ip="<IP>" [15m])))
```

### 2.3 Verificar Comprometimento
Verificar se o IP atacante obteve sucesso em algum momento:
```logql
{job="taskflow", event="login_success"} | json | client_ip="<IP>"
```

- **SE o resultado for maior que zero:** Conta comprometida. Classificar como Severidade ALTA e executar imediatamente a Contenção de Conta (Seção 3.2).
- **SE o resultado for vazio:** Ataque contido sem invasão. Manter Severidade MÉDIA e executar a Contenção de Rede (Seção 3.1).

---

## 3. Contenção, Erradicação e Recuperação

### 3.1 Contenção de Rede
1. **Ativar Rate Limit no Nginx:**
   - Descomentar as diretivas `limit_req_zone` e `limit_req` em `deploy/nginx/nginx.conf`.
   - Reiniciar o proxy:
     ```bash
     docker compose restart proxy
     ```
2. **Bloqueio de IP:**
   - Remover o IP atacante de `allowed_cidr` no arquivo `infra/main.tf` ou aplicar regra de bloqueio em firewall/NACL.

### 3.2 Contenção de Conta (Em caso de sucesso confirmado)
1. **Revogar Sessões Ativas:**
   - Atualizar a variável `TASKFLOW_SECRET_KEY` no arquivo `.env`.
   - Reiniciar a aplicação para invalidar todos os cookies de sessão existentes:
     ```bash
     docker compose up -d app
     ```
2. **Redefinir Credenciais:**
   - Alterar a senha da conta atingida via CLI da aplicação:
     ```bash
     docker compose exec app flask --app 'app:create_app()' create-user <usuario>
     ```

### 3.3 Erradicação e Recuperação
1. Executar a consulta de disparo e validar se o total de falhas do IP atacante retornou para 0.
2. Manter monitoramento ativo no Painel 1 por 30 minutos consecutivos.

---

## 4. Atividades Pós-Incidente

1. Documentar o tempo decorrido para detecção (TTD) e para resposta (TTR).
2. Submeter Pull Request tornando permanente a regra de rate limit no Nginx.
3. Configurar canal de alerta automático no Grafana com a mesma consulta de disparo.

---

## 5. Registro da Simulação

| Parâmetro | Resultado |
|---|---|
| Comando Executado | `./scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25` |
| Disparo Identificado | IP `172.21.0.1` atingiu 25 falhas (limiar: >10 falhas/5min) |
| Comprometimento | Consulta de `login_success` retornou 0 (nenhuma invasão) |
| Ação de Contenção | Rate limiting ativado no Nginx com resposta HTTP 503 |
| Auditoria de Dados | Busca por `senha-errada` no Loki retornou 0 registros |
