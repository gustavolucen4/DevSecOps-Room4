variable "aws_region" {
  description = "Região AWS."
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "AZ fixa: evita que a lista de zonas mude sozinha entre applies."
  type        = string
  default     = "us-east-1a"
}

variable "project_name" {
  description = "Prefixo dos recursos."
  type        = string
  default     = "taskflow"
}

# Sem default de propósito: quem aplica precisa informar o IP/CIDR do grupo (ex.: 200.1.2.3/32).
variable "allowed_cidr" {
  description = "Único CIDR autorizado a acessar SSH e HTTPS da instância."
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && var.allowed_cidr != "0.0.0.0/0"
    error_message = "Informe um CIDR válido e restrito; 0.0.0.0/0 não é aceito."
  }
}

variable "instance_type" {
  description = "Tipo da instância que roda o Compose da TaskFlow."
  type        = string
  default     = "t3.small"
}

variable "public_key_path" {
  description = "Chave pública SSH usada no key pair."
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "root_volume_size" {
  description = "Tamanho (GB) do volume raiz."
  type        = number
  default     = 20
}

variable "lab_instance_profile_name" {
  description = "Instance profile existente (AWS Academy não permite criar IAM)."
  type        = string
  default     = "LabInstanceProfile"
}

variable "log_retention_days" {
  description = "Retenção dos access logs e flow logs no bucket de logs."
  type        = number
  default     = 365
}
