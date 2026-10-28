output "public_ip" {
  description = "Elastic IP da instância (acesso restrito a var.allowed_cidr)."
  value       = aws_eip.app.public_ip
}

output "instance_id" {
  description = "ID da EC2."
  value       = aws_instance.app.id
}

output "artifacts_bucket" {
  description = "Bucket privado e criptografado de artefatos/backup da TaskFlow."
  value       = aws_s3_bucket.artifacts.bucket
}

output "logs_bucket" {
  description = "Bucket que recebe os access logs do S3 e os flow logs da VPC."
  value       = aws_s3_bucket.logs.bucket
}
