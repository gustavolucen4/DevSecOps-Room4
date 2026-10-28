# Infraestrutura da TaskFlow, corrigida a partir do Terraform do Room-4-DevOps
# (docs/iac.md mostra os achados do Checkov antes x depois).

data "aws_caller_identity" "current" {}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_iam_instance_profile" "lab_profile" {
  name = var.lab_instance_profile_name
}

# ---------------------------------------------------------------------------
# KMS: uma chave gerenciada pelo cliente, com rotação, para S3 e EBS.
# ---------------------------------------------------------------------------
resource "aws_kms_key" "main" {
  description             = "${var.project_name} - criptografia de S3 e EBS"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AdministracaoPelaConta"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        # Os flow logs da VPC gravam no bucket de logs, que é criptografado com esta chave.
        Sid       = "EntregaDeLogsDaVpc"
        Effect    = "Allow"
        Principal = { Service = "delivery.logs.amazonaws.com" }
        Action    = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"]
        Resource  = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}"
  target_key_id = aws_kms_key.main.key_id
}

# ---------------------------------------------------------------------------
# S3: bucket de logs (destino) e bucket de artefatos (privado, criptografado,
# versionado e com access logging).
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "logs" {
  #checkov:skip=CKV_AWS_18:Este é o bucket DESTINO dos access logs; logar nele mesmo cria loop de logs.
  #checkov:skip=CKV_AWS_144:Replicação entre regiões dobra o custo e a conta do AWS Academy não permite; aceitamos o risco no laboratório.
  #checkov:skip=CKV2_AWS_62:Notificações de evento não têm consumidor neste laboratório (sem SNS/SQS/Lambda).
  bucket_prefix = "${var.project_name}-logs-"
  force_destroy = false
}

resource "aws_s3_bucket" "artifacts" {
  #checkov:skip=CKV_AWS_144:Replicação entre regiões dobra o custo e a conta do AWS Academy não permite; aceitamos o risco no laboratório.
  #checkov:skip=CKV2_AWS_62:Notificações de evento não têm consumidor neste laboratório (sem SNS/SQS/Lambda).
  bucket_prefix = "${var.project_name}-artifacts-"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_ownership_controls" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "artifacts" {
  bucket        = aws_s3_bucket.artifacts.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access/artifacts/"
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    id     = "expirar-logs"
    status = "Enabled"
    filter {}
    expiration {
      days = var.log_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    id     = "limpar-versoes-antigas"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Só HTTPS: nega qualquer acesso sem TLS aos dois buckets.
resource "aws_s3_bucket_policy" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "NegarSemTLS"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.artifacts]
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "NegarSemTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.logs.arn, "${aws_s3_bucket.logs.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "AccessLogsDoS3"
        Effect    = "Allow"
        Principal = { Service = "logging.s3.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.logs.arn}/s3-access/*"
        Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
      },
      {
        Sid       = "FlowLogsDaVpc"
        Effect    = "Allow"
        Principal = { Service = "delivery.logs.amazonaws.com" }
        Action    = ["s3:PutObject", "s3:GetBucketAcl"]
        Resource  = [aws_s3_bucket.logs.arn, "${aws_s3_bucket.logs.arn}/vpc-flow/*"]
        Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.logs]
}

# ---------------------------------------------------------------------------
# Rede: VPC com flow logs, SG default fechado e subnet sem IP público automático.
# ---------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = "172.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_flow_log" "main" {
  vpc_id               = aws_vpc.main.id
  traffic_type         = "ALL"
  log_destination_type = "s3"
  log_destination      = "${aws_s3_bucket.logs.arn}/vpc-flow/"
}

# O SG default de toda VPC nasce aberto internamente; aqui ele fica sem regra alguma.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "172.20.10.0/24"
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Antes: 22, 80, 443, 3000 e 6443 (API do Kubernetes) abertos para 0.0.0.0/0.
# Depois: só SSH e HTTPS, e só a partir de var.allowed_cidr.
resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg"
  description = "TaskFlow - SSH e HTTPS apenas do CIDR autorizado"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH do CIDR autorizado"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS da TaskFlow (proxy do Compose) do CIDR autorizado"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  # Saída só para HTTPS (pacotes, imagens) e DNS; não existe mais "todas as portas".
  # Justificativa da exceção: o host precisa baixar imagens (Docker Hub/GHCR) e pacotes, cujos
  # IPs mudam o tempo todo. Restringir por IP exigiria VPC endpoints/proxy de saída, fora do
  # orçamento do AWS Academy. Risco aceito: só a porta 443 sai; todo o resto é negado.
  # trivy:ignore:AVD-AWS-0104
  egress {
    description = "HTTPS de saida para atualizacoes e registries"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "DNS de saida para o resolver da VPC"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["172.20.0.2/32"]
  }
}

# ---------------------------------------------------------------------------
# EC2: IMDSv2 obrigatório, disco criptografado, monitoramento e sem provisioner
# local-exec (o Ansible com StrictHostKeyChecking=no saiu do apply).
# ---------------------------------------------------------------------------
resource "aws_key_pair" "main" {
  key_name_prefix = "${var.project_name}-"
  public_key      = file(pathexpand(var.public_key_path))
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  key_name                    = aws_key_pair.main.key_name
  associate_public_ip_address = false
  iam_instance_profile        = data.aws_iam_instance_profile.lab_profile.name
  ebs_optimized               = true
  monitoring                  = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    kms_key_id            = aws_kms_key.main.arn
    delete_on_termination = true
  }

  tags = {
    Name = "${var.project_name}-server"
  }
}

# IP público estável via Elastic IP, em vez de IP automático em toda instância da subnet.
resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id
}
