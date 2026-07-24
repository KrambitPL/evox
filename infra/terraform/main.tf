data "aws_caller_identity" "current" {}
data "aws_secretsmanager_secret" "pioneer" { arn = var.pioneer_secret_arn }
data "aws_secretsmanager_secret" "sponsors" { arn = var.sponsor_secret_arn }

locals {
  name               = "evox-${var.environment}"
  api_image          = "${var.api_image_repository}@${var.api_image_digest}"
  web_image          = "${var.web_image_repository}@${var.web_image_digest}"
  secret_arns        = [data.aws_secretsmanager_secret.pioneer.arn, data.aws_secretsmanager_secret.sponsors.arn]
  log_retention_days = var.environment == "production" ? 90 : 30
  desired_count      = var.environment == "production" ? 2 : 1
  origin_domain_name = "origin-${var.domain_name}"
}

resource "aws_s3_bucket" "evidence" {
  bucket_prefix = "${local.name}-evidence-"
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket                  = aws_s3_bucket.evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_kms_key" "evidence" {
  description             = "Evox ${var.environment} evidence encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "evidence" {
  name          = "alias/${local.name}-evidence"
  target_key_id = aws_kms_key.evidence.key_id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.evidence.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

data "aws_iam_policy_document" "evidence_transport" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.evidence.arn,
      "${aws_s3_bucket.evidence.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "evidence_transport" {
  bucket = aws_s3_bucket.evidence.id
  policy = data.aws_iam_policy_document.evidence_transport.json
}

resource "aws_dynamodb_table" "state" {
  name         = "${local.name}-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}

resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${local.name}-jobs-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "jobs" {
  name                       = "${local.name}-jobs"
  visibility_timeout_seconds = 900
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_efs_file_system" "durable" {
  encrypted       = true
  kms_key_id      = aws_kms_key.durable.arn
  throughput_mode = "elastic"
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
}

resource "aws_kms_key" "durable" {
  description             = "Evox ${var.environment} durable worker storage encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "durable" {
  name          = "alias/${local.name}-durable"
  target_key_id = aws_kms_key.durable.key_id
}

resource "aws_efs_backup_policy" "durable" {
  file_system_id = aws_efs_file_system.durable.id
  backup_policy {
    status = "ENABLED"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}/api"
  retention_in_days = local.log_retention_days
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name}/worker"
  retention_in_days = local.log_retention_days
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name}/web"
  retention_in_days = local.log_retention_days
}
