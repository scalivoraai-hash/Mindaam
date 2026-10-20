locals {
  tags = { Application = "PULSEWORLD", Environment = "staging", ManagedBy = "Terraform" }
  secrets = merge(var.provider_secret_arns, { DATABASE_URL = var.database_url_secret_arn })
}
resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  vpc_id = var.vpc_id
  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "tasks" {
  name_prefix = "${var.name}-tasks-"
  vpc_id = var.vpc_id
  ingress {
    from_port = 8000
    to_port = 8000
    protocol = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  ingress {
    from_port = 3000
    to_port = 3000
    protocol = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "data" {
  name_prefix = "${var.name}-data-"
  vpc_id = var.vpc_id
  ingress {
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
  ingress {
    from_port = 6379
    to_port = 6379
    protocol = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
}
resource "aws_db_subnet_group" "main" {
  name = var.name
  subnet_ids = var.private_subnet_ids
}
resource "aws_db_instance" "main" {
  identifier = var.name
  engine = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  max_allocated_storage = 100
  storage_encrypted = true
  db_name = "pulseworld"
  username = "pulseworld_admin"
  manage_master_user_password = true
  db_subnet_group_name = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.data.id]
  publicly_accessible = false
  multi_az = var.database_multi_az
  backup_retention_period = 7
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.name}-final"
  auto_minor_version_upgrade = true
  tags = local.tags
}
resource "aws_elasticache_subnet_group" "main" {
  name = var.name
  subnet_ids = var.private_subnet_ids
}
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = var.name
  description = "PULSEWORLD presence and ephemeral state"
  node_type = "cache.t4g.micro"
  engine = "redis"
  engine_version = "7.1"
  num_cache_clusters = 2
  automatic_failover_enabled = true
  multi_az_enabled = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.data.id]
  snapshot_retention_limit = 1
  tags = local.tags
}
resource "aws_s3_bucket" "media" {
  bucket_prefix = "${var.name}-media-"
  force_destroy = false
  tags = local.tags
}
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_cloudwatch_log_group" "main" {
  name = "/ecs/${var.name}"
  retention_in_days = 30
}
resource "aws_iam_role" "execution" {
  name = "${var.name}-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "execution" {
  role = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role_policy" "secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = values(local.secrets) }] })
}
resource "aws_iam_role" "task" {
  name = "${var.name}-task"
  assume_role_policy = aws_iam_role.execution.assume_role_policy
}
resource "aws_ecs_cluster" "main" {
  name = var.name
  setting {
    name = "containerInsights"
    value = "enabled"
  }
}
resource "aws_lb" "main" {
  name = var.name
  load_balancer_type = "application"
  security_groups = [aws_security_group.alb.id]
  subnets = var.public_subnet_ids
  drop_invalid_header_fields = true
  idle_timeout = 120
}
resource "aws_lb_target_group" "app" {
  for_each = { api = 8000, web = 3000 }
  name = "${var.name}-${each.key}"
  port = each.value
  protocol = "HTTP"
  vpc_id = var.vpc_id
  target_type = "ip"
  deregistration_delay = 30
  health_check {
    path = each.key == "api" ? "/ready" : "/"
    matcher = "200"
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port = 443
  protocol = "HTTPS"
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn = var.certificate_arn
  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.app["web"].arn
  }
}
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority = 10
  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.app["api"].arn
  }
  condition {
    path_pattern { values = ["/api/*", "/health", "/ready", "/ws/*"] }
  }
}
resource "aws_ecs_task_definition" "app" {
  for_each = { api = { image = var.api_image, port = 8000 }, web = { image = var.web_image, port = 3000 } }
  family = "${var.name}-${each.key}"
  network_mode = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu = 512
  memory = 1024
  execution_role_arn = aws_iam_role.execution.arn
  task_role_arn = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name = each.key
    image = each.value.image
    essential = true
    user = each.key == "api" ? "10001" : "1000"
    portMappings = [{ containerPort = each.value.port, protocol = "tcp" }]
    environment = each.key == "api" ? [
      { name = "APP_ENV", value = "staging" },
      { name = "PUBLIC_ORIGIN", value = var.public_origin },
      { name = "PUBLIC_APP_URL", value = var.public_origin },
      { name = "REDIS_URL", value = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0" }
    ] : [{ name = "NODE_ENV", value = "production" }]
    secrets = each.key == "api" ? [for name, arn in local.secrets : { name = name, valueFrom = arn }] : []
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.main.name, awslogs-region = var.region, awslogs-stream-prefix = each.key } }
  }])
}
resource "aws_ecs_service" "app" {
  for_each = aws_ecs_task_definition.app
  name = "${var.name}-${each.key}"
  cluster = aws_ecs_cluster.main.id
  task_definition = each.value.arn
  desired_count = var.desired_count
  launch_type = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent = 200
  health_check_grace_period_seconds = 60
  deployment_circuit_breaker {
    enable = true
    rollback = true
  }
  network_configuration {
    subnets = var.private_subnet_ids
    security_groups = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.app[each.key].arn
    container_name = each.key
    container_port = each.key == "api" ? 8000 : 3000
  }
  depends_on = [aws_lb_listener.https, aws_iam_role_policy.secrets]
}
