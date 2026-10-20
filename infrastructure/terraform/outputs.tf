output "load_balancer_dns" { value = aws_lb.main.dns_name }
output "database_endpoint" { value = aws_db_instance.main.address }
output "database_master_secret_arn" {
  value = aws_db_instance.main.master_user_secret[0].secret_arn
  sensitive = true
}
output "cluster_name" { value = aws_ecs_cluster.main.name }
output "api_task_definition" { value = aws_ecs_task_definition.app["api"].arn }
output "media_bucket" { value = aws_s3_bucket.media.id }
