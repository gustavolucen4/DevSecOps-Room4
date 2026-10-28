# Segurança em IaC (Módulo 5)

## Docker Compose (`docker-compose.yml`)

| Requisito | Como foi atendido |
|---|---|
| Redes isoladas | `frontend` (só proxy e Grafana publicam porta, em `127.0.0.1`), `backend` com `internal: true` (proxy ↔ app) e `observability` com `internal: true` (Promtail → Loki ← Grafana) |
| Banco sem porta no host | A TaskFlow usa SQLite: o "banco" é o volume `taskflow-data`, montado **só** no serviço `app`, sem `ports:`. A app também não publica porta, e o acesso é só pelo proxy |
| Segredos via `.env` | `TASKFLOW_SECRET_KEY` e `GRAFANA_ADMIN_PASSWORD` com `${VAR:?}`: o Compose não sobe sem eles. O `.env` está no `.gitignore` e só o `.env.example` é versionado |
| `read_only` | Todos os serviços, com `tmpfs /tmp` (`noexec,nosuid`) e volumes só onde há escrita |
| `healthcheck` | `app`, `proxy` e `grafana`. O `proxy` só sobe depois de a `app` estar *healthy* |
| Limites de CPU, memória e PIDs | `deploy.resources.limits` em todos os serviços |
| `no-new-privileges` e `cap_drop: ALL` | Âncora `x-hardening` aplicada a todos os serviços |
| Imagens fixadas | Tag **e** digest `sha256` em nginx, Loki, Promtail e Grafana |
| Sem `docker.sock` | O Promtail lê o log da app por volume somente-leitura (`taskflow-logs:ro`) |

**Decisão (SQLite x Postgres):** mantivemos o SQLite da Atividade 1 para não reescrever a camada de dados e os testes. O controle exigido ("banco sem porta exposta") é garantido porque o volume do banco só existe dentro da rede `backend`, que é `internal`. Se o grupo migrar para Postgres, ele entra na mesma rede `backend`, sem `ports:`.

## Terraform (`infra/`)

A base é o Terraform do Room-4-DevOps (VPC, EC2 e SG), corrigido e acrescido do bucket S3 exigido pela atividade. `terraform validate` passa, e no CI ele roda com `-backend=false`, sem credencial da AWS.

| Antes (Room-4-DevOps) | Achado | Depois (`infra/main.tf`) |
|---|---|---|
| SG com 22, 80, 443, 3000 e **6443 (API Kubernetes)** abertos para `0.0.0.0/0` | CKV_AWS_24, CKV_AWS_260, Trivy AWS-0107 | Só 22 e 443, a partir de `var.allowed_cidr`. A variável **não tem default** e rejeita `0.0.0.0/0` |
| Egress em todas as portas | CKV_AWS_382, Trivy AWS-0104 | Saída só 443 (com exceção justificada no código) e DNS para o resolver da VPC |
| IMDSv1 habilitado | CKV_AWS_79, Trivy AWS-0028 | `http_tokens = "required"`, hop limit 1 |
| Disco raiz sem criptografia | Trivy AWS-0131 | `encrypted = true` com chave KMS própria, com rotação |
| IP público automático na subnet e na EC2 | CKV_AWS_130, CKV_AWS_88, Trivy AWS-0164 | `map_public_ip_on_launch = false` e Elastic IP explícito |
| Sem flow logs; SG default aberto | CKV2_AWS_11, CKV2_AWS_12 | `aws_flow_log` para o bucket de logs; `aws_default_security_group` sem regras |
| Sem monitoramento e sem EBS otimizado | CKV_AWS_126, CKV_AWS_135 | `monitoring = true`, `ebs_optimized = true` |
| `local-exec` rodando Ansible com `StrictHostKeyChecking=no` | MITM no provisionamento | Provisioner removido do apply |
| **Sem bucket S3** | — | `artifacts`: **privado** (public access block + `BucketOwnerEnforced`), **criptografado** (SSE-KMS), **versionado**, **com access logging** para o bucket `logs`, lifecycle e política que nega acesso sem TLS |

**Checkov:** antes, 11 falhas; depois, **57 passed, 0 failed, 5 skipped**. Trivy config (HIGH/CRITICAL): antes 5, depois 0. Evidências em `docs/evidencias/atividade-2/checkov-*.txt` e `trivy-config-*.txt`.

### Skips, todos justificados no próprio recurso

| Check | Recurso | Justificativa |
|---|---|---|
| CKV_AWS_18 | `aws_s3_bucket.logs` | É o bucket **destino** dos access logs; logar nele mesmo cria loop |
| CKV_AWS_144 (×2) | os dois buckets | Replicação entre regiões dobra o custo e não é permitida no AWS Academy |
| CKV2_AWS_62 (×2) | os dois buckets | Notificações de evento não têm consumidor (sem SNS/SQS/Lambda) |
| Trivy AVD-AWS-0104 | egress 443 do SG | Registries e pacotes mudam de IP; restringir exigiria VPC endpoints/proxy de saída |

## Pipeline (`.github/workflows/iac-scan.yml`)

Três jobs, cada um com seu required check: `IaC - Terraform validate`, `IaC - Checkov` (`soft_fail: false`) e `IaC - Trivy config` (`exit-code: 1` em HIGH/CRITICAL).

**Por que não há `paths:`:** um required check que só dispara quando um `.tf` muda deixa PRs que não tocam em infraestrutura travados para sempre, esperando um check que nunca roda. O custo de rodar sempre é de 1 a 2 minutos por PR. O benefício é que o gate nunca fica "pendente", e mudanças no `Dockerfile` também passam pelo Checkov e pelo Trivy.

Para a **demo**, em um PR troque `cidr_blocks = [var.allowed_cidr]` do SSH por `["0.0.0.0/0"]`. O Checkov (CKV_AWS_24) e o Trivy (AWS-0107) reprovam. Reverta e o check volta a ficar verde.
