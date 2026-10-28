# Roteiro da Apresentação — Atividade 2 (Lab de DAST, IaC e Observabilidade)

**Duração:** aproximadamente 10 minutos (cronometrados).  
**Repositório Oficial:** [https://github.com/gustavolucen4/DevSecOps-Room4](https://github.com/gustavolucen4/DevSecOps-Room4)  
**Grupo (Room 4):** Gustavo Lucena, Júlio Santos, Frederico Cavalcanti, Felipe Almeida, Pedro Holanda.

---

## 🖥️ Preparação Obrigatória (Antes da Apresentação)

1. Deixe o Docker Compose rodando localmente no host:
   ```bash
   cp .env.example .env
   docker compose up -d
   ```
2. Deixe as seguintes abas abertas no navegador:
   * **Aba 1 (Home do Repositório):** [https://github.com/gustavolucen4/DevSecOps-Room4](https://github.com/gustavolucen4/DevSecOps-Room4)
   * **Aba 2 (Demo DAST - PR #2):** [https://github.com/gustavolucen4/DevSecOps-Room4/pull/2](https://github.com/gustavolucen4/DevSecOps-Room4/pull/2)
   * **Aba 3 (Demo IaC - PR #3):** [https://github.com/gustavolucen4/DevSecOps-Room4/pull/3](https://github.com/gustavolucen4/DevSecOps-Room4/pull/3)
   * **Aba 4 (Grafana Local):** [http://127.0.0.1:3000](http://127.0.0.1:3000) no dashboard **TaskFlow - Segurança e Login**
   * **Aba 5 (Runbook NIST):** [docs/runbook-login-bruteforce.md](runbook-login-bruteforce.md)
3. Deixe uma janela de terminal aberta pronta para rodar o script de força bruta:
   ```bash
   ./scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25
   ```

---

## ⏱️ Minutagem e Divisão de Papéis

### 🕒 0:00 a 1:30 — Bloco 1: Contexto e Evolução (Membros e Papéis)
* **Tela:** Aba 1 (Página inicial do repositório no GitHub).
* **Objetivo:** Explicar a evolução da esteira estática (Atividade 1) para o ciclo completo em runtime (Atividade 2).
* **Fala sugerida:**
  > *"Olá, professor e colegas. Na Atividade 1, construímos a base da nossa esteira de DevSecOps focada no código estático (SAST com Semgrep, Gitleaks, SCA e Hardening do container).  
  > Na **Atividade 2**, fechamos o ciclo de segurança de ponta a ponta:  
  > 1. Validamos a aplicação em execução com **DAST no pipeline** (OWASP ZAP Baseline e Full Scan ativo);  
  > 2. Endurecemos a **Infraestrutura como Código** com Terraform (S3 KMS, SG restrito) e Docker Compose seguro, auditados por Checkov e Trivy;  
  > 3. Implementamos **Observabilidade defensiva** com logs estruturados em JSON contendo `request_id`, stack Grafana + Loki + Promtail, e um plano formal de resposta a incidentes baseado no **NIST SP 800-61**."*

---

### 🕒 1:30 a 4:00 — Bloco 2: Demonstração ao Vivo do DAST (Módulo 4)
* **Tela:** Aba 2 (PR #2: Regressão de XSS).
* **Objetivo:** Mostrar o DAST reprovando uma falha real em tempo de execução e o Quality Gate bloqueando o merge.
* **Passos da Demonstração:**
  1. Mostrar o PR #2: um commit que reintroduziu a vulnerabilidade trocando `{{ error }}` por `{{ error | safe }}` no template de login.
  2. Apontar o status check **`DAST - ZAP Baseline` em vermelho** e o botão de Merge **bloqueado**.
  3. Explicar o que o ZAP fez:
     * O workflow executou uma **espera ativa com curl no `/login`** (até 60s) antes do scan, garantindo que o ZAP não atacasse o nada.
     * O ZAP Full Scan ativo injetou o payload `</p><script>alert(1);</script><p>` no campo de usuário e detectou o XSS refletido (Regra 40012).
  4. Mostrar a solução na branch `main`: templates Jinja2 com autoescape limpo sem nenhum `| safe` (tratando os sinks de erro de login e o parâmetro `q` da busca), `/debug/info` removido e `.zap/rules.tsv` versionado com justificativas.

---

### 🕒 4:00 a 6:00 — Bloco 3: Segurança em IaC (Módulo 5)
* **Tela:** Aba 3 (PR #3: SSH Aberto) e o arquivo `docker-compose.yml`.
* **Objetivo:** Mostrar a auditoria de infraestrutura reprovando configurações inseguras.
* **Passos da Demonstração:**
  1. Mostrar o PR #3: alteração no Terraform abrindo a porta 22 (SSH) para `0.0.0.0/0`.
  2. Apontar os checks **`IaC - Checkov`** e **`IaC - Trivy config` reprovados**, bloqueando a mesclagem.
  3. Destacar as correções da `main`:
     * **Terraform (`infra/main.tf`):** SSH e HTTPS restritos estritamente à variável `allowed_cidr` (rejeitando `0.0.0.0/0`), S3 bucket privado com criptografia SSE-KMS com rotação de chave, versionamento e access logging.
     * **Docker Compose (`docker-compose.yml`):** redes `frontend`, `backend` e `observability` isoladas, banco SQLite em volume sem porta no host, containers em `read_only`, sem capabilities e Promtail sem montar o `docker.sock`.

---

### 🕒 6:00 a 8:30 — Bloco 4: Incidente ao Vivo e Runbook NIST (Módulo 6 — Ponto Alto!)
* **Tela:** Terminal + Aba 4 (Grafana) + Aba 5 (Runbook NIST).
* **Objetivo:** Exercitar o ataque simulado, mostrar a detecção imediata no Grafana e percorrer as 4 fases do NIST SP 800-61.
* **Passos da Demonstração:**
  1. **Executar o ataque no terminal:**
     ```bash
     ./scripts/simular-forca-bruta.sh http://127.0.0.1:8080 admin 25
     ```
  2. **Atualizar o Grafana (Aba 4):**
     * Mostrar o gráfico subindo em tempo real no dashboard **TaskFlow - Segurança e Login**.
     * Apontar a query de disparo do runbook atingindo o limiar de anomalia (> 10 falhas/5min):
       ```logql
       sum by (client_ip) (count_over_time({job="taskflow", event="login_failed"} | json [5m])) > 10
       ```
  3. **Percorrer as 4 fases do NIST no Runbook (Aba 5):**
     * **Fase 1 (Preparação):** Logs estruturados em JSON, stack Loki e Grafana provisionada.
     * **Fase 2 (Detecção e Análise):** Executar a query de comprometimento `{job="taskflow", event="login_success"} | json | client_ip="<IP>"`. Como retorna vazio, sabemos que o ataque não obteve êxito (severidade Média).
     * **Fase 3 (Contenção e Erradicação):** Aplicação de rate limiting no Nginx (10 req/min) ou bloqueio no Security Group. Se houvesse invasão, rotação da `TASKFLOW_SECRET_KEY` derrubaria as sessões.
     * **Fase 4 (Atividades Pós-Incidente):** Métricas de TTD e TTR e refinamento de alertas.
  4. **A Prova de Ouro:**
     * Mostrar que a busca no Loki por `senha-errada` retorna **0 linhas**, comprovando que credenciais nunca são vazadas nos logs.

---

### 🕒 8:30 a 10:00 — Bloco 5: Trade-offs Técnicos e Conclusão
* **Tela:** Aba 1 (README ou Rulesets).
* **Objetivo:** Explicar decisões de arquitetura e responder às perguntas da banca.
* **Pontos de Destaque:**
  1. **Ausência de filtro `paths:` no `iac-scan.yml` (Prevenção de deadlock em PRs):**
     * *Contexto:* O `iac-scan.yml` provê 3 checks obrigatórios (*Required Status Checks*) na proteção da `main`: `IaC - Terraform validate`, `IaC - Checkov` e `IaC - Trivy config`.
     * *O Problema:* Se configurássemos um filtro restrito como `paths: ['infra/**', 'docker-compose*.yml']`, qualquer Pull Request que alterasse apenas código de aplicação (ex: `app.py` ou `templates/`) **não dispararia o workflow**. O GitHub aguardaria indefinidamente o status check ser reportado, criando um **bloqueio perpétuo de merge**.
     * *Decisão:* O pipeline executa em todo PR. Dura ~1 min, elimina o risco de travar entregas e assegura auditoria contínua de IaC e containers.
  2. **Política do OWASP ZAP (Flag `-I` e regras em `FAIL` no `.zap/rules.tsv`):**
     * *Contexto:* No CI, o ZAP roda localmente no runner em HTTP (`127.0.0.1:5000`), sem certificado TLS de produção.
     * *O Problema:* No modo padrão, o ZAP reprovaria o job por avisos puramente informativos de ambiente (ex: cookie sem flag `Secure` em HTTP ou falta de HSTS), gerando falsos-positivos e fadiga de alertas. Desligar o scanner ou usar `continue-on-error`, porém, desarmaria a proteção.
     * *Decisão:* Execução com `-I` (ignorar warnings genéricos) somada ao arquivo `rules.tsv` versionado. Regras críticas de injeção (XSS 40012/40014, SQLi) e má configuração (CSP, anti-CSRF) são marcadas como **`FAIL`** (bloqueantes). Regras de infraestrutura/TLS no runner são documentadas como **`WARN`** com justificativa técnica formal.
  3. **Isolamento de Dados:** Manutenção do SQLite em volume montado apenas na rede interna `backend` sem porta no host garantiu conformidade total sem overhead desnecessário de infraestrutura.

---

## 📁 Evidências de Apoio (Plano B)

Caso a conexão ou o container local oscilem durante a apresentação, utilize as evidências consolidadas já salvas no repositório:
* DAST Antes × Depois: `docs/evidencias/atividade-2/zap-base-after.html` e `zap-full-vuln.html`
* Checkov e Trivy: `docs/evidencias/atividade-2/checkov-after.txt` e `trivy-config-after.txt`
* Detecção no Grafana: `docs/evidencias/atividade-2/grafana-forca-bruta.jpg`
