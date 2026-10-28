"""Pure renderers: JSON is valid YAML for Cloud Run, Compose, LiveKit and Caddy."""
from urllib.parse import urlsplit
from common import SETTINGS


def environment(c, env, origin):
    ordinary = {"APP_ENV": env, "PUBLIC_ORIGIN": origin, "PUBLIC_APP_URL": origin,
                "RUN_MIGRATIONS_ON_START": "false", "DB_POOL_SIZE": "3", "DB_MAX_OVERFLOW": "2",
                "LIVEKIT_URL": "wss://" + SETTINGS["media_domain"],
                "LIVEKIT_HOST_ALLOWLIST": SETTINGS["media_domain"]}
    secrets = {k: f"mindaam-{env}-{suffix}" for k, suffix in {
        "DATABASE_URL": "database-url", "REDIS_URL": "redis-url", "LIVEKIT_API_KEY": "livekit-key",
        "LIVEKIT_API_SECRET": "livekit-secret", "PULSEPOINT_SECRET": "pulsepoint-secret",
        "MAIL_ENCRYPTION_KEY": "mail-encryption-key", "SUPER_ADMIN_EMAIL": "owner-email",
        "SUPER_ADMIN_USERNAME": "owner-username", "SUPER_ADMIN_INITIAL_PASSWORD": "owner-password"}.items()}
    from release_policy import profile, BETA
    if profile() == BETA:
        ordinary["MINDAAM_PAYMENT_ACTIONS_ENABLED"] = "false"
    return ordinary, secrets


def service(c, env, image, origin, optional=None):
    ordinary, secrets = environment(c, env, origin)
    secrets.update(optional or {})
    return {"apiVersion": "serving.knative.dev/v1", "kind": "Service",
            "metadata": {"name": "mindaam-" + env, "labels": {"application": "mindaam", "environment": env},
                         "annotations": {"run.googleapis.com/maxScale": str(SETTINGS[env + "_max_instances"])}},
            "spec": {"template": {"metadata": {"annotations": {
                "autoscaling.knative.dev/minScale": "0", "autoscaling.knative.dev/maxScale": str(SETTINGS[env + "_max_instances"]),
                "run.googleapis.com/cpu-throttling": "true", "run.googleapis.com/startup-cpu-boost": "false",
                "run.googleapis.com/cloudsql-instances": f"{c.project}:{c.region}:mindaam-postgres",
                "run.googleapis.com/network-interfaces": '[{"network":"mindaam","subnetwork":"mindaam-run"}]',
                "run.googleapis.com/vpc-access-egress": "private-ranges-only"}},
                "spec": {"serviceAccountName": c.sa(env), "containerConcurrency": SETTINGS["cloud_run_concurrency"],
                         "timeoutSeconds": 3600, "containers": [{"image": image, "ports": [{"containerPort": 3000}],
                         "resources": {"limits": {"cpu": SETTINGS["cloud_run_cpu"], "memory": SETTINGS["cloud_run_memory"]}},
                         "env": [{"name": k, "value": v} for k, v in ordinary.items()] + [
                             {"name": k, "valueFrom": {"secretKeyRef": {"name": v, "key": "latest"}}} for k, v in secrets.items()],
                         "startupProbe": {"httpGet": {"path": "/api/health", "port": 3000}, "periodSeconds": 5, "failureThreshold": 48},
                         "livenessProbe": {"httpGet": {"path": "/api/health", "port": 3000}, "periodSeconds": 30, "failureThreshold": 3}}]}}}}


def caddy_config(production_origin=None):
    media, turn = SETTINGS["media_domain"], SETTINGS["turn_domain"]
    hosts = [media, turn]
    routes = []
    for host, port in [(turn, 5349), (media, 7880)]:
        tls = {"handler": "tls"}
        if host == media:
            tls["connection_policies"] = [{"alpn": ["http/1.1"]}]
        routes.append({"match": [{"tls": {"sni": [host]}}], "handle": [tls, {"handler": "proxy", "upstreams": [{"dial": [f"127.0.0.1:{port}"]}]}]})
    apps = {"tls": {"certificates": {"automate": hosts}}, "layer4": {"servers": {"main": {"listen": [":443"], "routes": routes}}}}
    if production_origin:
        upstream = urlsplit(production_origin)
        if upstream.scheme != "https" or not (upstream.hostname or "").endswith(".run.app") or upstream.path not in ("", "/") or upstream.username or upstream.password or upstream.query or upstream.fragment or upstream.port not in (None, 443):
            raise ValueError("Only the verified production Cloud Run HTTPS origin is allowed.")
        hosts.append(SETTINGS["domain"])
        routes.append({"match": [{"tls": {"sni": [SETTINGS["domain"]]}}], "handle": [
            {"handler": "tls", "connection_policies": [{"alpn": ["http/1.1"]}]},
            {"handler": "proxy", "upstreams": [{"dial": ["127.0.0.1:9080"]}]}]})
        apps["http"] = {"servers": {"app": {"listen": ["127.0.0.1:9080"], "routes": [{"handle": [{
            "handler": "reverse_proxy", "upstreams": [{"dial": upstream.hostname + ":443"}],
            "transport": {"protocol": "http", "tls": {"server_name": upstream.hostname}},
            "headers": {"request": {"set": {"Host": [upstream.hostname], "X-Forwarded-Proto": ["https"], "X-Forwarded-Host": [SETTINGS["domain"]]}}}}]}]}}}
    return {"logging": {"logs": {"default": {"level": "WARN"}}}, "storage": {"module": "file_system", "root": "/data"}, "apps": apps}


def livekit_config(keys):
    return {"port": 7880, "bind_addresses": ["0.0.0.0"],
            "rtc": {"tcp_port": 7881, "port_range_start": 50000, "port_range_end": 50200, "use_external_ip": True},
            "keys": keys, "turn": {"enabled": True, "domain": SETTINGS["turn_domain"], "tls_port": 5349, "udp_port": 3478, "external_tls": True},
            "logging": {"level": "warn"}}


def compose_config():
    services = {}
    for name, memory, cpu in [("redis", "256m", 0.3), ("livekit", "1g", 1.2), ("caddy", "256m", 0.5)]:
        filename = "redis.conf" if name == "redis" else name + ".json"
        commands = {"redis": ["redis-server", "/run/mindaam/redis.conf"], "livekit": ["--config", "/run/mindaam/livekit.json"],
                    "caddy": ["run", "--config", "/run/mindaam/caddy.json"]}
        services[name] = {"image": SETTINGS["images"][name], "command": commands[name], "network_mode": "host", "restart": "unless-stopped",
                          "read_only": True, "cap_drop": ["ALL"], "security_opt": ["no-new-privileges:true"],
                          "mem_limit": memory, "cpus": cpu, "volumes": [f"/run/mindaam/{filename}:/run/mindaam/{filename}:ro"],
                          "logging": {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}}}
    services["redis"]["entrypoint"] = ["redis-server"]
    services["redis"]["command"] = ["/run/mindaam/redis.conf"]
    services["caddy"]["cap_add"] = ["NET_BIND_SERVICE"]
    services["caddy"]["tmpfs"] = ["/config:rw,noexec,nosuid,size=8m"]
    services["caddy"]["volumes"].append("/var/lib/mindaam/caddy:/data")
    return {"services": services}


def postgres(c):
    # Cloud SQL API exposes these fields consistently, including SDKs whose GA
    # `instances create` CLI does not yet expose labels/auto-resize limits.
    return {"name": "mindaam-postgres", "region": c.region, "databaseVersion": "POSTGRES_16",
            "settings": {"tier": SETTINGS["sql_tier"], "edition": "ENTERPRISE", "availabilityType": "ZONAL",
                         "userLabels": {"application": "mindaam", "managed_by": "mindaam-github"},
                         "dataDiskType": "PD_SSD", "dataDiskSizeGb": str(SETTINGS["sql_disk_gb"]),
                         "storageAutoResize": True, "storageAutoResizeLimit": str(SETTINGS["sql_disk_limit_gb"]),
                         "deletionProtectionEnabled": True, "activationPolicy": "ALWAYS",
                         "ipConfiguration": {"ipv4Enabled": True, "authorizedNetworks": [], "sslMode": "ENCRYPTED_ONLY"},
                         "backupConfiguration": {"enabled": True, "startTime": "03:00", "pointInTimeRecoveryEnabled": True,
                                                 "transactionLogRetentionDays": 7,
                                                 "backupRetentionSettings": {"retentionUnit": "COUNT", "retainedBackups": 7}}}}
