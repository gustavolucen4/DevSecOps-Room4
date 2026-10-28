# Resumo da Atividade 2 — Lab de DAST, IaC e Observabilidade

Este documento consolida os entregáveis, controles e evidências geradas para a avaliação da **Atividade 2**, com mapeamento direto às rubricas da disciplina.

---

## 📋 Mapeamento de Entregas e Quality Gates

| Módulo / Rubrica | Requisito Avaliado | O que foi Implementado | Evidência Comprovada |
| :--- | :--- | :--- | :--- |
| **Módulo 4: DAST (25%)** | Aplicação atacada em runtime pelo ZAP; XSS e debug corrigidos; gate bloqueante. | • Templates Jinja2 com autoescape limpo sem `\| safe` em todos os sinks (busca e erro do login).<br>• `/debug/info` removido e debug controlado por env var.<br>• Headers de segurança injetados (CSP, XFO, nosniff).<br>• [`.github/workflows/dast.yml`](../.github/workflows/dast.yml) com polling ativo no `/login` (até 60s) e ZAP Full Scan ativo.<br>• [`.zap/rules.tsv`](../.zap/rules.tsv) com regra 40012 em FAIL e sem regras em IGNORE. | • PR #2 demonstrando merge bloqueado por XSS.<br>• Relatórios HTML em [`docs/evidencias/atividade-2/`](evidencias/atividade-2/): `zap-base-after.html` e `zap-full-vuln.html`.<br>• Mapeamento OWASP Top 10 em [`docs/dast.md`](dast.md). |
| **Módulo 5: IaC Segura (20%)** | Compose e Terraform sem falhas clássicas; Checkov e Trivy config como quality gates. | • [`docker-compose.yml`](../docker-compose.yml): 3 redes isoladas, SQLite em volume sem porta no host, reverse proxy Nginx sem privilégios, `read_only`, sem capabilities e Promtail sem `docker.sock`.<br>• [`infra/main.tf`](../infra/main.tf): S3 privado, SSE-KMS com rotação, versionamento e access logging. SG restrito a `var.allowed_cidr`. IMDSv2 e EBS criptografado.<br>• [`.github/workflows/iac-scan.yml`](../.github/workflows/iac-scan.yml): Checkov (`soft_fail: false`) e Trivy config (`exit-code: 1`), sem filtro `paths:`. | • PR #3 demonstrando Checkov e Trivy reprovando porta 22 aberta.<br>• Saídas reais de scan em [`docs/evidencias/atividade-2/`](evidencias/atividade-2/): `checkov-after.txt` (57 passed, 0 failed) e `trivy-config-after.txt` (0 HIGH/CRITICAL).<br>• Documentação em [`docs/iac.md`](iac.md). |
| **Módulo 6: Observabilidade (15%)** | Logging estruturado em JSON com `request_id`, nada sensível logado, stack no ar. | • Logs JSON no stdout e volume com `ts`, `level`, `request_id`, `client_ip` (ProxyFix) e eventos (`login_success`, `login_failed`, `task_created`, etc.).<br>• Filtro estrito: **zero senhas**, tokens CSRF ou cookies nos logs.<br>• Stack Grafana + Loki + Promtail provisionada via Compose com dashboard pré-carregado. | • 6 consultas LogQL documentadas em [`docs/observabilidade.md`](observabilidade.md).<br>• Teste automatizado `test_logs_are_json_without_secrets` aprovado.<br>• Busca por `senha-errada` no Loki retornando 0 linhas. |
| **Módulo 6: Resposta a Incidentes (15%)** | Ataque simulado detectado nos logs; runbook com 4 fases do NIST SP 800-61. | • Script [`scripts/simular-forca-bruta.sh`](../scripts/simular-forca-bruta.sh) enviando tentativas com tokens CSRF reais.<br>• Runbook [`docs/runbook-login-bruteforce.md`](runbook-login-bruteforce.md) com condição de disparo (> 10 falhas/5min), query de comprometimento e contenção no Nginx. | • Detecção real no Grafana registrada em `docs/evidencias/atividade-2/grafana-forca-bruta.jpg`.<br>• Registro do exercício no próprio runbook. |
| **Governança & Higiene (10%)** | .env fora do Git, permissions mínimas, actions pinadas por SHA, 9 required checks. | • `.env` no `.gitignore`; apenas `.env.example` versionado.<br>• `permissions: contents: read` em todos os workflows.<br>• Todas as actions fixadas por commit SHA imutável.<br>• Ruleset da `main` com os 9 checks obrigatórios e branch protection ativa. | • Ruleset verificado via API GitHub (`ruleset_id: 26004352`).<br>• Repositório privado com `@HardSource` convidado. |
| **Apresentação (15%)** | Demonstração ao vivo funcional, respeito ao tempo (~10 min), todos falam. | • Roteiro detalhado com minutagem e divisão de papéis em [`docs/apresentacao-atividade-2.md`](apresentacao-atividade-2.md).<br>• Branches de demonstração prontas (`demo/xss-regressao` e `demo/iac-ssh-aberto`). | • PRs #2 e #3 mantidos como rascunhos e com merge bloqueado para a demo ao vivo. |

---

## 🛠️ Comandos para Reproduzir Localmente

```bash
# 1. Configurar variáveis e subir o ambiente completo:
cp .env.example .env
docker compose up -d --build

# 2. Criar usuário seguro para testes:
docker compose exec app flask --app 'app:create_app()' create-user gustavo --password 'SenhaForte123!'

# 3. Disparar a simulação de força bruta:
./scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25

# 4. Acessar os serviços:
# - Aplicação TaskFlow: http://127.0.0.1:8080/login
# - Grafana (Dashboard de Segurança): http://127.0.0.1:3000 (admin / senha do .env)
```
