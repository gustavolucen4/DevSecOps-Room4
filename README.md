# DevSecOps & Esteira Segura — Room 4 DevOps Pós
### TaskFlow — Quality Gates, Hardening, DAST, IaC e Observabilidade em CI/CD

Repositório unificado de Engenharia de Software / DevSecOps cobrindo a esteira completa de validação segura: desde a governança com proteção de branch e Quality Gates automatizados no GitHub Actions (CI/SAST/SCA), passando pela correção de vulnerabilidades no código (`app.py`), até o hardening e auditoria de containers com Trivy e runtime restrito.

---

## 👥 Membros da Equipe
* **@Shuralot** — Júlio Santos
* **@jfredericocavalcanti** — Frederico Cavalcanti
* **@gustavolucen4** — Gustavo Lucena Silva
* **@fabalmeida** — Felipe Almeida
* **@holandalelis** — Pedro Holanda Lelis
* *(Colaborador / Coautor)*: **@diegobuarquebr** — Diego Buarque

---

## 📋 Checklist da Atividade 1 (Lab de Esteira Segura)
- [x] **Repositório Privado & Acesso de Avaliação:** Repositório configurado como privado com o professor `@HardSource` adicionado como colaborador (permissão *Read*).
- [x] **Branch `main` Protegida (Governança):** Pull Request obrigatório, revisão mandatória via [`.github/CODEOWNERS`](.github/CODEOWNERS) e merge estritamente condicionado a 5 *Required Status Checks*.
- [x] **Pipeline de CI Básico ([`ci.yml`](.github/workflows/ci.yml)):** Instalação com verificação de hashes (`--require-hashes`), linting com `ruff`, compilação de bytecode e suíte de testes unitários de regressão (`pytest`).
- [x] **Pipeline de SAST & Segredos ([`sast.yml`](.github/workflows/sast.yml)):** Análise estática com Semgrep (`p/python`, `p/flask`, `p/security-audit`, flag `--error`) e secret scanning completo no histórico com Gitleaks (`fetch-depth: 0`).
- [x] **Correções no Código da Aplicação ([`app.py`](app.py)):**
  - **SQL Injection:** Consultas 100% parametrizadas com placeholders `?` no login, cadastro e buscas.
  - **Segredo de Sessão:** Remoção de chave estática; `SECRET_KEY` lida obrigatoriamente de `TASKFLOW_SECRET_KEY` do ambiente, abortando se ausente.
  - **Senhas:** Eliminação de texto puro; hashing com salt via `Werkzeug` e comando CLI interativo com senha mínima de 12 dígitos sem eco.
  - **CSRF:** Proteção CSRF ativada com `Flask-WTF`.
- [x] **Pipeline de SCA & Dependências ([`sca.yml`](.github/workflows/sca.yml)):** Auditoria com `pip-audit --require-hashes` bloqueando vulnerabilidades conhecidas (CVEs) e [`.github/dependabot.yml`](.github/dependabot.yml) ativo com checagens periódicas.
- [x] **Hardening de Container ([`Dockerfile`](Dockerfile)):** Correção das 6 falhas clássicas (base Alpine com tag e digest fixados, usuário não-root `10001:10001`, ausência de segredos em `ENV/ARG`, servidor Gunicorn de produção, debug desligado e instalação enxuta).
- [x] **Scan de Imagem & Runtime Seguro ([`container.yml`](.github/workflows/container.yml)):** Build da imagem, scan de vulnerabilidades com Trivy (`--severity HIGH,CRITICAL --exit-code 1`) e inicialização em sandbox restrito ([`scripts/docker-run-seguro.sh`](scripts/docker-run-seguro.sh)).
- [x] **Demonstração do Shift-Left:** PR com vulnerabilidade controlada gerando falha bloqueante na esteira e posterior liberação após commit corretivo.
- [x] **Documentação & Evidências:** Relatório comparativo antes × depois documentado em [`docs/hardening.md`](docs/hardening.md) e [`docs/evidencias/`](docs/evidencias/).

---

## 📋 Checklist da Atividade 2 (Lab de DAST, IaC e Observabilidade)

- [x] **XSS corrigido** com Jinja2 e autoescape (sem `| safe`), incluindo os sinks do Encontro 9: o parâmetro `q` da busca e a mensagem de erro do login. Veja [`docs/dast.md`](docs/dast.md).
- [x] **`/debug/info` removido.** O debug é controlado por `TASKFLOW_DEBUG` e fica **desligado por padrão**. Headers de segurança (CSP, XFO, nosniff…) foram adicionados via `after_request`.
- [x] **[`dast.yml`](.github/workflows/dast.yml):** build da imagem, TaskFlow subindo no runner, **espera ativa no `/login`**, ZAP Baseline e ZAP Full Scan como gate, e relatórios publicados como artefato.
- [x] **[`.zap/rules.tsv`](.zap/rules.tsv)** versionado: cada WARN tem justificativa e o XSS (40012/40014) é FAIL. Achados antes × depois mapeados ao OWASP Top 10 em [`docs/dast.md`](docs/dast.md).
- [x] **[`docker-compose.yml`](docker-compose.yml) seguro:**
  - redes `frontend`, `backend` (internal) e `observability` (internal);
  - banco sem porta no host;
  - segredos via `.env` (não versionado) + [`.env.example`](.env.example);
  - `read_only`, `healthcheck`, limites de CPU, memória e PIDs, `no-new-privileges` e `cap_drop: ALL`;
  - imagens fixadas por digest.
- [x] **Terraform [`infra/main.tf`](infra/main.tf)**, corrigido a partir do Terraform do Room-4-DevOps:
  - S3 privado, SSE-KMS, versionado e com access logging;
  - SG restrito a `var.allowed_cidr`;
  - IMDSv2, EBS criptografado e flow logs;
  - `terraform validate` passando. Veja [`docs/iac.md`](docs/iac.md).
- [x] **[`iac-scan.yml`](.github/workflows/iac-scan.yml):** `terraform validate`, Checkov e Trivy config como gates. Todo `#checkov:skip` e `trivy:ignore` tem justificativa no próprio código.
- [x] **Logging estruturado em JSON** com `request_id` por requisição e os eventos `login_success`, `login_failed`, `task_created` e `task_list`, sem senha, token ou cookie. Coberto por teste.
- [x] **Grafana + Loki + Promtail via Compose**, com datasource e dashboard provisionados. [`docs/observabilidade.md`](docs/observabilidade.md) traz 6 consultas LogQL, incluindo falhas de login por IP.
- [x] **Simulação de força bruta** com [`scripts/simular-forca-bruta.sh`](scripts/simular-forca-bruta.sh), detectada no Grafana. O runbook NIST SP 800-61 está em [`docs/runbook-login-bruteforce.md`](docs/runbook-login-bruteforce.md).

### Arquitetura da Atividade 2 (app, rede e observabilidade)

```text
        Navegador / ZAP / script de força bruta
                        │  127.0.0.1:8080
 ┌──────────── rede frontend ─────────────┐        127.0.0.1:3000
 │  proxy (nginx-unprivileged)            │   ┌──────────────────────┐
 │  X-Request-ID, X-Forwarded-For,        │   │ grafana              │
 │  rate limit (contenção do runbook)     │   │ dashboard provisionado│
 └───────────────┬────────────────────────┘   └─────────┬────────────┘
   rede backend  │ (internal: sem saída, sem porta)      │ rede observability
                 ▼                                       │ (internal)
   ┌──────────────────────────┐   volume taskflow-logs   ▼
   │ app (TaskFlow/Gunicorn)  │ ── JSON ──► promtail ──► loki
   │ read_only, non-root      │     (ro, sem docker.sock)
   │ SQLite em taskflow-data  │
   └──────────────────────────┘
```

### Como subir e como disparar cada workflow

```bash
cp .env.example .env                      # troque TASKFLOW_SECRET_KEY e GRAFANA_ADMIN_PASSWORD
docker compose up -d --build              # TaskFlow em :8080, Grafana em :3000
docker compose run --rm app flask --app 'app:create_app()' create-user <usuario>
scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 40   # simulação do Módulo 6
```

| Workflow | Disparo | Required check(s) |
|---|---|---|
| `ci.yml`, `sast.yml`, `sca.yml`, `container.yml` | PR, push na `main`, manual | os 5 da Atividade 1 |
| `dast.yml` | PR, push na `main`, manual (**Actions → DAST → Run workflow**) | `DAST - ZAP Baseline` |
| `iac-scan.yml` | PR, push na `main`, manual (**Actions → IaC Scan → Run workflow**) | `IaC - Terraform validate`, `IaC - Checkov`, `IaC - Trivy config` |

**Por que o `iac-scan.yml` não tem `paths:`:** ele é um required check. Se só rodasse quando um `.tf` muda, PRs que não tocam em infraestrutura ficariam travados esperando um check que nunca roda. Rodar sempre custa cerca de 1 a 2 min por PR e também cobre mudanças no `Dockerfile`.

### Decisão técnica e trade-off (para a apresentação)

**O ZAP roda com `-I` + lista explícita de FAIL, em vez de "todo alerta bloqueia".**
- **Ganho:** o gate não fica vermelho por alertas informativos (10111, 10112, 10109), e as categorias críticas (XSS, SQLi, headers, cookies, CSRF, debug) bloqueiam o merge.
- **Custo:** um tipo de alerta novo, fora da lista, só aparece no relatório até alguém promovê-lo a FAIL.
- **Complemento:** somamos um **Full Scan ativo limitado a 10 min**. O Baseline é passivo e não consegue provar o XSS refletido sozinho.

---

## 🏗️ Arquitetura da Esteira Segura (Quality Gates)

A esteira atua como barreira de contenção obrigatória para qualquer alteração de código ou configuração proposta para a branch `main`:

```text
       [ Desenvolvedor / Feature Branch ]
                       │
                       ▼
          [ Pull Request para `main` ]
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
[ GitHub Actions CI ]       [ Branch Protection ]
         │                           │
         ├─► ci.yml                  │  Regra da `main`:
         │   • Hashes & Ruff Lint    │  • Bloqueia Push direto
         │   • Testes com Pytest     │  • Exige CODEOWNERS
         │                           │  • Exige 5 Checks Verdes:
         ├─► sast.yml                │    1. CI - build lint testes
         │   • Semgrep (--error)     │    2. SAST - Semgrep
         │   • Gitleaks (histórico)  │    3. Segredos - Gitleaks
         │                           │    4. SCA - pip-audit
         ├─► sca.yml                 │    5. Container - build e Trivy
         │   • pip-audit bloqueante  │
         │                           │
         └─► container.yml           │
             • Build Dockerfile      │
             • Trivy (HIGH/CRITICAL) │
             • Smoke test em runtime │
                       │             │
                       ▼             ▼
             [ Todos os Checks Aprovados? ]
                       │
              ┌────────┴────────┐
              ▼ (SIM)           ▼ (NÃO)
       [ Merge Liberado ]  [ Merge Bloqueado ]
              │                 │
              ▼                 ▼
       [ Branch `main` ]   [ Rejeição & Correção ]
```

---

## 🛡️ Topologia dos Quality Gates e Mecanismos de Bloqueio

| Quality Gate | Workflow | Ferramenta / Alvo | Mecanismo de Bloqueio |
| :--- | :--- | :--- | :--- |
| **Lint & Sintaxe** | `ci.yml` | Ruff & `compileall` em `app.py` / `tests` | Falha o job caso haja violações de estilo ou erros de sintaxe. |
| **Testes Unitários** | `ci.yml` | `pytest -q` | Falha o job se alguma regressão funcional for introduzida. |
| **SAST** | `sast.yml` | Semgrep (`p/python`, `p/flask`, `p/security-audit`) | Flag `--error` encerra com exit-code `1` se houver achados de código inseguro. |
| **Secret Scanning** | `sast.yml` | Gitleaks (`fetch-depth: 0`) | Reprova o job ao detectar credenciais ou tokens em qualquer commit do histórico. |
| **SCA** | `sca.yml` | `pip-audit --require-hashes -r requirements.txt` | Reprova o job se houver dependências com CVEs conhecidas sem correção. |
| **Container Scan** | `container.yml` | Trivy (`image-ref: taskflow:ci`) | Flag `--exit-code 1` para severidades `HIGH,CRITICAL` bloqueia imagens vulneráveis. |

---

## 🔄 Estratégia de Shift-Left e Procedimento de Demonstração

### Cenário de Demonstração (Gate em Ação)
1. **Injeção de Falha Controlada:** Abre-se um Pull Request a partir de uma branch de teste reintroduzindo concatenação direta de SQL na rota de login de `app.py`.
2. **Execução do Quality Gate:** O GitHub Actions dispara imediatamente o `sast.yml`. O Semgrep identifica o padrão inseguro e a flag `--error` encerra o job com código de saída `1` (check vermelho).
3. **Bloqueio do Merge:** A regra de *Branch Protection* da `main` reconhece o status check reprovado e **bloqueia o botão de Merge**, impedindo a integração do código vulnerável.
4. **Correção no Mesmo PR:** O desenvolvedor substitui a concatenação pela consulta parametrizada com placeholders (`?`) e envia o commit na mesma branch.
5. **Aprovação e Desbloqueio:** O pipeline reexecuta, todos os 5 status checks concluem verdes e o GitHub desbloqueia a mesclagem na `main`.

---

## ⚙️ Workflows do Repositório

| Workflow | Arquivo | Gatilhos | Finalidade |
| :--- | :--- | :--- | :--- |
| **CI** | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | `pull_request`, `push: [main]`, `workflow_dispatch` | Instala pacotes conferindo hashes SHA256, executa linting via Ruff, compila bytecode e roda testes com Pytest. |
| **SAST e Segredos** | [`.github/workflows/sast.yml`](.github/workflows/sast.yml) | `pull_request`, `push: [main]`, `workflow_dispatch` | Varredura estática com Semgrep bloqueante e análise do histórico Git completo com Gitleaks. |
| **SCA** | [`.github/workflows/sca.yml`](.github/workflows/sca.yml) | `pull_request`, `push: [main]`, `workflow_dispatch` | Análise de vulnerabilidades conhecidas em bibliotecas terceiras com `pip-audit`. |
| **Container** | [`.github/workflows/container.yml`](.github/workflows/container.yml) | `pull_request`, `push: [main]`, `workflow_dispatch` | Constrói imagem Docker, executa scan de vulnerabilidades com Trivy e testa inicialização com Gunicorn. |
| **Dependabot** | [`.github/dependabot.yml`](.github/dependabot.yml) | Agendamento semanal | Propõe Pull Requests automáticos para atualização de bibliotecas `pip`, actions do GitHub e imagem base Docker. |

---

## 💻 Como Rodar os Checks e a Aplicação Localmente

### 1. Configurar Ambiente Virtual e Dependências
```powershell
# No PowerShell (Windows):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependências fixadas com conferência estrita de hashes:
python -m pip install --require-hashes -r requirements.txt
python -m pip install pytest==9.1.1 ruff==0.17.1 pip-audit==2.10.1 pip-tools==7.6.2
```

### 2. Executar os Gates de Qualidade Localmente
```bash
# 1. Análise estática de código e formatação (Ruff)
ruff check app.py tests

# 2. Testes de regressão (Pytest)
pytest -q

# 3. Auditoria de dependências (SCA)
pip-audit --require-hashes -r requirements.txt

# 4. Análise estática avançada (SAST com Semgrep)
semgrep scan --config=p/python --config=p/flask --config=p/security-audit --error .

# 5. Detecção de segredos no histórico (Gitleaks)
gitleaks git . --redact
```

### 3. Rodar a Aplicação Localmente com Docker e Trivy
```bash
# 1. Build da imagem com hardening
docker build -t taskflow:hardened .

# 2. Scan de vulnerabilidades de container com Trivy (severidades altas e críticas)
trivy image --severity HIGH,CRITICAL --exit-code 1 taskflow:hardened

# 3. Execução em runtime seguro (sandbox restrito)
export TASKFLOW_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
bash scripts/docker-run-seguro.sh

# 4. Criar usuário seguro no banco de dados da aplicação
docker exec -it taskflow-seguro flask --app 'app:create_app()' create-user aluno
```

---

## 🌐 Como Acessar a Aplicação pelo Navegador

A aplicação em container expõe a porta `5000` vinculada localmente ao host (`127.0.0.1`):

* **URL de Acesso:** [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
* **Credenciais:** Criadas via CLI interativa (`create-user`) sem senhas pré-definidas em código ou imagem.
* **Segurança de Sessão:** Cookie configurado com `HttpOnly`, `SameSite=Lax` e `Secure` (habilitado por padrão para produção/HTTPS; parametrizável via `TASKFLOW_HTTPS=0` para desenvolvimento local).

---

## 🧠 Decisões Técnicas e Trade-offs

1. **Consultas Parametrizadas em vez de Concatenação:**
   Todas as chamadas SQL utilizam placeholders `?` fornecidos pela biblioteca nativa `sqlite3`. Isso separa a semântica da consulta dos dados informados pelo usuário, neutralizando completamente vetores de SQL Injection sem exigir dependências pesadas de ORMs externos.

2. **Gestão de Segredos e Hashing de Senhas:**
   A credencial `ADMIN_PASSWORD` foi erradicada da imagem Docker e do código. A chave de sessão `SECRET_KEY` é alimentada obrigatoriamente pela variável de ambiente `TASKFLOW_SECRET_KEY` em tempo de execução. As senhas de usuários utilizam hash com salt criptográfico via Werkzeug (`generate_password_hash` e `check_password_hash`), impedindo a exposição de senhas mesmo em eventual leitura não autorizada da base SQLite.

3. **Base Mínima Alpine com Pinned Digest e Atualização do SO:**
   Optou-se pela base `python:3.12.13-alpine3.23` fixada por versão e digest OCI imutável (`@sha256:...`). Executa-se `apk upgrade --no-cache` na camada de build para sanar vulnerabilidades conhecidas dos pacotes do sistema operacional, reduzindo o resultado do Trivy de **388 ocorrências HIGH/CRITICAL** para **zero**, sem utilizar supressões artificiais (`.trivyignore`).

4. **Runtime Restrito e Isolamento de Privilégios:**
   A aplicação roda sob usuário e grupo não-root dedicados (`USER 10001:10001`). O script [`scripts/docker-run-seguro.sh`](scripts/docker-run-seguro.sh) impõe sistema de arquivos raiz somente-leitura (`--read-only`), remove todas as capabilities do kernel Linux (`--cap-drop=ALL`), desabilita elevação de privilégios (`--security-opt=no-new-privileges`) e isola dados transitórios em `tmpfs`.

5. **Tratamento Cirúrgico de Exceções no Gitleaks:**
   Durante a varredura profunda com `fetch-depth: 0`, o scanner apontou chaves públicas GPG da imagem base oficial do Python presentes no histórico. Em conformidade com as rubricas da disciplina, não se desativou o scanner nem a regra: registrou-se uma allowlist cirúrgica em [`.gitleaksignore`](.gitleaksignore) contendo exclusivamente os fingerprints públicos envolvidos, preservando o gate ativo para qualquer credencial real.

6. **Boas Práticas de Pipeline as Code:**
   Todos os arquivos de workflow operam sob o princípio do privilégio mínimo com `permissions: contents: read`. As GitHub Actions de terceiros são estritamente fixadas por SHA imutável (comentadas com a tag semântica) e gerenciadas automaticamente pelo Dependabot semanal.
