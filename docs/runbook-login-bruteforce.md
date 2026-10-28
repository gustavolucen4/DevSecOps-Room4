# Runbook — Força bruta no login da TaskFlow

Estrutura NIST SP 800-61 (Computer Security Incident Handling Guide), com 4 fases.

| Campo | Valor |
|---|---|
| Serviço | TaskFlow (`POST /login`) |
| Severidade inicial | Média. Sobe para **Alta** se a consulta de confirmação mostrar `login_success` do IP atacante |
| Dono | SRE de plantão do grupo, com o dev responsável pela TaskFlow como apoio |
| Painel | Grafana → TaskFlow → **TaskFlow - Segurança e Login** |

## Condição de disparo

**Mais de 10 `login_failed` vindos do mesmo `client_ip` em 5 minutos.**

Query de detecção, a mesma do painel 2:
```logql
sum by (client_ip) (count_over_time({job="taskflow", event="login_failed"} | json [5m])) > 10
```

Por que 10: um usuário legítimo que errou a senha raramente passa de 3 a 5 tentativas. Acima de 10 por IP em 5 minutos é automação.

## 1. Preparação

Isto já existe antes do incidente:
- Logs JSON com `request_id`, `client_ip`, `username` e `event`, sem senha (`docs/observabilidade.md`).
- Stack Loki, Promtail e Grafana no ar, com o dashboard provisionado em `observability/grafana/dashboards/`.
- O proxy nginx é o ponto único de entrada, onde a contenção é aplicada (rate limit pronto e comentado em `deploy/nginx/nginx.conf`).
- O script `scripts/simular-forca-bruta.sh` serve para exercitar este runbook.
- Contatos e canal: abrir thread no canal do grupo com o prefixo `[INCIDENTE] bruteforce-login`.

## 2. Detecção e análise

1. **Confirme o alerta** no Grafana, painel 2 ou Explore, com a query de disparo acima. Anote o(s) `client_ip` e a contagem.
2. **Descubra o alvo:** quais contas estão sendo atacadas?
   ```logql
   topk(5, sum by (username) (count_over_time({job="taskflow", event="login_failed"} | json | client_ip="<IP>" [15m])))
   ```
3. **Verifique se houve comprometimento.** Esta é a pergunta mais importante:
   ```logql
   {job="taskflow", event="login_success"} | json | client_ip="<IP>"
   ```
   - Se vier **vazio**, o ataque não teve sucesso e a severidade fica **Média**.
   - Se vier **qualquer linha**, a conta foi comprometida e a severidade passa a **Alta**. Siga direto para a contenção da conta (passo 3b).
4. **Caracterize o ataque:** `user_agent`, intervalo entre tentativas e se o mesmo IP faz outras ações:
   ```logql
   {job="taskflow"} | json | client_ip="<IP>" | line_format "{{.ts}} {{.event}} {{.path}} {{.status}} {{.user_agent}}"
   ```
5. **Registre** na thread do incidente: horário de início, IP(s), contas visadas, total de tentativas, houve sucesso (sim/não) e os `request_id` de exemplo.

## 3. Contenção, erradicação e recuperação

**Contenção (minutos):**
- a. **Rate limit no proxy:** em `deploy/nginx/nginx.conf`, descomente `limit_req_zone` e `limit_req` (10 POSTs/min por IP) e rode `docker compose restart proxy`.
- Se for um único IP, bloqueie também na borda. Na AWS, remova o IP do `allowed_cidr` do SG (`infra/`) ou adicione um `deny` na NACL.
- b. **Se houve login com sucesso:**
  - Invalide as sessões trocando a `TASKFLOW_SECRET_KEY` no `.env` e rodando `docker compose up -d app`. Isso derruba todas as sessões assinadas com a chave antiga.
  - Redefina a senha da conta afetada com `flask create-user` / atualização no banco.
  - Avise o dono da conta.

**Erradicação:**
- Confirme que a query de disparo voltou a **0** para o IP e que não há novos IPs.
- Revise as ações feitas pela conta comprometida, se houver, cruzando `task_created` e `task_list` pelo `user_id`.

**Recuperação:**
- Mantenha o rate limit ligado. Ele vira configuração padrão via PR no repositório, passando pelos gates.
- Acompanhe o painel 1 por 30 min. Feche a contenção de borda só depois de 24h sem nova ocorrência.

## 4. Atividades pós-incidente

Em até 5 dias úteis, faça uma revisão sem culpados:
- **Linha do tempo:** detecção → contenção → recuperação, com o tempo de cada etapa (TTD e TTR).
- **O que funcionou e o que faltou.** Exemplos: alerta automático no Grafana em vez de olhar o painel; bloqueio de conta após N falhas; MFA.
- **Ações com dono e prazo, abertas como issues.** Exemplos:
  - tornar o rate limit padrão no nginx;
  - criar uma regra de alerta no Grafana com a mesma query;
  - adicionar atraso progressivo no `/login`.
- **Atualize este runbook** se algum passo não funcionou como descrito.

## Registro do exercício (simulação do grupo)

| Item | Resultado |
|---|---|
| Ataque | `scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25` |
| Detecção | A query de disparo retornou `client_ip="172.19.0.1"` com **25** falhas em 5 min (limiar: 10) |
| Comprometimento | A query de `login_success` para o IP voltou vazia, então **não houve** |
| Contenção | Rate limit do nginx ativado; as tentativas seguintes recebem `503` do proxy |
| Vazamento de dado sensível | A busca por `senha-errada` no Loki retornou **0 linhas** |
