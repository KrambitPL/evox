resource "aws_ecs_cluster" "this" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public HTTPS entrypoint for Evox"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "tasks" {
  name        = "${local.name}-tasks"
  description = "Evox application tasks reachable only through the ALB"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "worker" {
  name        = "${local.name}-worker"
  description = "Evox worker tasks with no inbound network access"
  vpc_id      = var.vpc_id
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

data "aws_vpc" "selected" { id = var.vpc_id }

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
}

resource "aws_vpc_security_group_egress_rule" "alb_api" {
  security_group_id            = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.tasks.id
}

resource "aws_vpc_security_group_egress_rule" "alb_web" {
  security_group_id            = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
  referenced_security_group_id = aws_security_group.tasks.id
}

resource "aws_vpc_security_group_ingress_rule" "tasks_api" {
  security_group_id            = aws_security_group.tasks.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_ingress_rule" "tasks_web" {
  security_group_id            = aws_security_group.tasks.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
  referenced_security_group_id = aws_security_group.alb.id
}

# Public HTTPS is required for the explicitly configured sponsor APIs.
#trivy:ignore:AWS-0104
resource "aws_vpc_security_group_egress_rule" "tasks_https" {
  security_group_id = aws_security_group.tasks.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

# Public HTTPS is required for the explicitly configured sponsor APIs.
#trivy:ignore:AWS-0104
resource "aws_vpc_security_group_egress_rule" "worker_https" {
  security_group_id = aws_security_group.worker.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "tasks_dns_udp" {
  security_group_id = aws_security_group.tasks.id
  ip_protocol       = "udp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"
}

resource "aws_vpc_security_group_egress_rule" "tasks_dns_tcp" {
  security_group_id = aws_security_group.tasks.id
  ip_protocol       = "tcp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"
}

resource "aws_vpc_security_group_egress_rule" "worker_dns_udp" {
  security_group_id = aws_security_group.worker.id
  ip_protocol       = "udp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"
}

resource "aws_vpc_security_group_egress_rule" "worker_dns_tcp" {
  security_group_id = aws_security_group.worker.id
  ip_protocol       = "tcp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"
}

resource "aws_security_group" "efs" {
  name        = "${local.name}-efs"
  description = "NFS access from Evox worker tasks only"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "efs" {
  security_group_id            = aws_security_group.efs.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  referenced_security_group_id = aws_security_group.worker.id
}

resource "aws_vpc_security_group_egress_rule" "worker_efs" {
  security_group_id            = aws_security_group.worker.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  referenced_security_group_id = aws_security_group.efs.id
}

resource "aws_efs_mount_target" "durable" {
  for_each        = toset(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.durable.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "worker" {
  file_system_id = aws_efs_file_system.durable.id
  posix_user {
    gid = 10001
    uid = 10001
  }
  root_directory {
    path = "/worker"
    creation_info {
      owner_gid   = 10001
      owner_uid   = 10001
      permissions = "0750"
    }
  }
}

# This internet-facing ALB is an intentional CloudFront origin; its ingress rule is
# restricted to the AWS-managed CloudFront origin prefix list.
#trivy:ignore:AWS-0053
resource "aws_lb" "api" {
  name                       = local.name
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = var.public_subnet_ids
  drop_invalid_header_fields = true
  enable_deletion_protection = var.environment == "production"
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path    = "/healthz"
    matcher = "200"
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern {
      values = ["/v1/*", "/healthz"]
    }
  }
  condition {
    http_header {
      http_header_name = "X-Evox-Origin-Verify"
      values           = local.origin_verify_headers
    }
  }
}

resource "aws_lb_listener_rule" "web" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 20
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
  condition {
    http_header {
      http_header_name = "X-Evox-Origin-Verify"
      values           = local.origin_verify_headers
    }
  }
}

locals {
  common_environment = [
    { name = "EVOX_AWS_REGION", value = var.aws_region },
    { name = "EVOX_DYNAMODB_TABLE", value = aws_dynamodb_table.state.name },
    { name = "EVOX_EVIDENCE_BUCKET", value = aws_s3_bucket.evidence.id },
    { name = "EVOX_JOBS_QUEUE_URL", value = aws_sqs_queue.jobs.url },
  ]
  sponsor_secrets = [
    { name = "PIONEER_API_KEY", valueFrom = "${data.aws_secretsmanager_secret.pioneer.arn}:PIONEER_API_KEY::" },
    { name = "SENSO_API_KEY", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:SENSO_API_KEY::" },
    { name = "ACTIAN_VECTORAI_URL", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:ACTIAN_VECTORAI_URL::" },
    { name = "ACTIAN_VECTORAI_ACCESS_TOKEN", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:ACTIAN_VECTORAI_ACCESS_TOKEN::" },
    { name = "EVOX_ACTIAN_OUTCOME_COLLECTION", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:EVOX_ACTIAN_OUTCOME_COLLECTION::" },
    { name = "EVOX_ACTIAN_VECTOR_SIZE", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:EVOX_ACTIAN_VECTOR_SIZE::" },
    { name = "EVOX_BAND_AGENT_ID", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:EVOX_BAND_AGENT_ID::" },
    { name = "EVOX_BAND_API_KEY", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:EVOX_BAND_API_KEY::" },
    { name = "EVOX_BAND_HUMAN_ID", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:EVOX_BAND_HUMAN_ID::" },
    { name = "EVOX_BAND_HUMAN_HANDLE", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:EVOX_BAND_HUMAN_HANDLE::" },
    { name = "GUILD_WORKSPACE_ID", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:GUILD_WORKSPACE_ID::" },
    { name = "GUILD_AGENT_ID", valueFrom = "${data.aws_secretsmanager_secret.sponsors.arn}:GUILD_AGENT_ID::" },
  ]
  origin_verify_headers = var.origin_verify_previous_header == null ? [
    var.origin_verify_header,
    ] : [
    var.origin_verify_header,
    var.origin_verify_previous_header,
  ]
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  volume { name = "tmp" }
  container_definitions = jsonencode([{
    name                   = "api", image = local.api_image, essential = true,
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }],
    environment            = local.common_environment, secrets = local.sponsor_secrets,
    readonlyRootFilesystem = true, user = "10001",
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }],
    logConfiguration       = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.api.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "api" } },
    healthCheck            = { command = ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8000/healthz\", timeout=3)'"], interval = 30, timeout = 5, retries = 3, startPeriod = 20 }
  }])
}

resource "aws_lb_target_group" "web" {
  name        = "${local.name}-web"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path    = "/"
    matcher = "200-399"
  }
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.web.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  volume { name = "tmp" }
  container_definitions = jsonencode([{
    name                   = "web", image = local.web_image, essential = true,
    portMappings           = [{ containerPort = 3000, protocol = "tcp" }],
    readonlyRootFilesystem = true, user = "10001",
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }],
    logConfiguration       = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.web.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "web" } }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.worker.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  volume { name = "tmp" }
  volume {
    name = "durable-work"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.durable.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.worker.id
        iam             = "DISABLED"
      }
    }
  }
  container_definitions = jsonencode([{
    name                   = "worker", image = local.api_image, essential = true, command = ["evox-worker"],
    environment            = local.common_environment, secrets = local.sponsor_secrets,
    readonlyRootFilesystem = true, user = "10001",
    mountPoints = [
      { sourceVolume = "durable-work", containerPath = "/var/lib/evox", readOnly = false },
      { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
    ],
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.worker.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "worker" } }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = local.desired_count
  launch_type     = "FARGATE"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener_rule.api]
}

resource "aws_ecs_service" "worker" {
  name            = "worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = local.desired_count
  launch_type     = "FARGATE"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = false
  }
  depends_on = [aws_efs_mount_target.durable]
}

resource "aws_ecs_service" "web" {
  name            = "web"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = local.desired_count
  launch_type     = "FARGATE"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }
  depends_on = [aws_lb_listener_rule.web]
}
