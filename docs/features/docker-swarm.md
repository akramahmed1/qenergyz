# Docker Swarm Deployment Guide

## Overview

This guide covers deploying the Qenergyz platform using Docker Swarm for hybrid cloud environments. Docker Swarm provides native clustering and orchestration capabilities for Docker containers.

## Prerequisites

### System Requirements

- Docker Engine 20.10+ on all nodes
- Docker Swarm mode initialized
- Minimum 3 manager nodes for production
- Load balancer (optional, for external access)

### Network Requirements

- Secure communication between nodes
- Persistent storage for databases
- External access to ports 80, 443, 8000

## Quick Start

### 1. Initialize Swarm

```bash
# On manager node
docker swarm init --advertise-addr <MANAGER_IP>

# On worker nodes (use token from above command)
docker swarm join --token <WORKER_TOKEN> <MANAGER_IP>:2377
```

### 2. Create Secrets

```bash
# Database password
echo "your_secure_password" | docker secret create qenergyz_db_password -

# Application secret key
echo "your_secret_key_32_chars_long!" | docker secret create qenergyz_secret_key -

# Encryption key
echo "your_encryption_key_32_chars!" | docker secret create qenergyz_encryption_key -
```

### 3. Create External Networks

```bash
docker network create --driver overlay qenergyz-overlay
```

### 4. Deploy Stack

```bash
docker stack deploy -c docker-stack.yml qenergyz
```

## Architecture Comparison

### Docker Compose vs Docker Swarm vs Kubernetes

| Feature | Compose | Swarm | Kubernetes |
|---------|---------|-------|------------|
| **Complexity** | Low | Medium | High |
| **Learning Curve** | Easy | Moderate | Steep |
| **Multi-host** | No | Yes | Yes |
| **Auto-scaling** | No | Basic | Advanced |
| **Load Balancing** | External | Built-in | Advanced |
| **Secret Management** | Limited | Built-in | Advanced |
| **Health Checks** | Basic | Good | Excellent |
| **Rolling Updates** | No | Yes | Yes |
| **Resource Limits** | Basic | Good | Advanced |

### When to Use Docker Swarm

**Advantages:**
- Simple setup and management
- Native Docker integration
- Built-in service discovery
- Easy secrets management
- Good for small to medium deployments

**Use Cases:**
- Hybrid cloud deployments
- Teams familiar with Docker
- Rapid prototyping and development
- Cost-sensitive deployments

## Configuration

### Stack Configuration

The `docker-stack.yml` file defines the complete Qenergyz application stack:

```yaml
version: '3.8'

services:
  qenergyz-backend:
    image: qenergyz/backend:latest
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
      update_config:
        parallelism: 1
        delay: 10s
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
```

### Service Placement

Control where services run using placement constraints:

```yaml
deploy:
  placement:
    constraints:
      - node.role == worker        # Worker nodes only
      - node.hostname == db-node   # Specific node
      - node.labels.tier == frontend  # Custom labels
```

### Resource Management

Set resource limits and reservations:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

## Production Deployment

### 1. Node Configuration

**Manager Nodes (3 minimum):**
```bash
# Label manager nodes
docker node update --label-add role=manager node1
docker node update --label-add role=manager node2
docker node update --label-add role=manager node3
```

**Worker Nodes:**
```bash
# Label worker nodes for specific services
docker node update --label-add tier=frontend worker1
docker node update --label-add tier=backend worker2
docker node update --label-add tier=database worker3
```

### 2. External Configuration

Create external configs for nginx and prometheus:

```bash
# Nginx configuration
docker config create nginx_config /path/to/nginx.conf

# Prometheus configuration
docker config create prometheus_config /path/to/prometheus.yml
```

### 3. Volume Management

For production, use external volume plugins:

```yaml
volumes:
  postgres-data:
    driver: nfs
    driver_opts:
      share: "nfs-server:/path/to/postgres-data"
```

### 4. High Availability Setup

```yaml
services:
  postgres:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.hostname == db-primary
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
```

## Monitoring and Logging

### Built-in Monitoring

Docker Swarm includes basic monitoring:

```bash
# Service status
docker service ls

# Service logs
docker service logs qenergyz_qenergyz-backend

# Node status
docker node ls

# Stack status
docker stack ps qenergyz
```

### External Monitoring

Grafana and Prometheus are included in the stack:

- **Grafana**: http://your-domain:3000 (admin/admin)
- **Prometheus**: http://your-domain:9090

### Logging Configuration

Configure logging drivers for centralized logging:

```yaml
services:
  qenergyz-backend:
    logging:
      driver: "gelf"
      options:
        gelf-address: "udp://logstash:12201"
        tag: "qenergyz-backend"
```

## Scaling

### Manual Scaling

```bash
# Scale backend service
docker service scale qenergyz_qenergyz-backend=5

# Scale multiple services
docker service scale qenergyz_qenergyz-backend=5 qenergyz_qenergyz-frontend=3
```

### Auto-scaling (Basic)

While Swarm doesn't have built-in auto-scaling, you can implement basic scaling with scripts:

```bash
#!/bin/bash
# Simple CPU-based scaling script

SERVICE="qenergyz_qenergyz-backend"
CPU_THRESHOLD=80
MAX_REPLICAS=10

CURRENT_CPU=$(docker stats --no-stream --format "table {{.CPUPerc}}" | grep -v CPU | sed 's/%//' | awk '{sum+=$1} END {print sum/NR}')

if (( $(echo "$CURRENT_CPU > $CPU_THRESHOLD" | bc -l) )); then
    CURRENT_REPLICAS=$(docker service inspect $SERVICE --format='{{.Spec.Mode.Replicated.Replicas}}')
    if [ $CURRENT_REPLICAS -lt $MAX_REPLICAS ]; then
        NEW_REPLICAS=$((CURRENT_REPLICAS + 1))
        docker service scale $SERVICE=$NEW_REPLICAS
        echo "Scaled $SERVICE to $NEW_REPLICAS replicas"
    fi
fi
```

## Security

### Network Security

```yaml
networks:
  qenergyz-overlay:
    driver: overlay
    driver_opts:
      encrypted: "true"    # Encrypt network traffic
    ipam:
      config:
        - subnet: 172.30.0.0/16
```

### Secrets Management

```bash
# Rotate secrets
echo "new_password" | docker secret create qenergyz_db_password_v2 -
docker service update --secret-rm qenergyz_db_password --secret-add qenergyz_db_password_v2 qenergyz_postgres
docker secret rm qenergyz_db_password
```

### Image Security

```yaml
services:
  qenergyz-backend:
    image: qenergyz/backend:v1.2.3  # Use specific tags
    deploy:
      placement:
        constraints:
          - node.labels.security == high
```

## Backup and Recovery

### Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec $(docker ps -qf "name=qenergyz_postgres") pg_dump -U qenergyz qenergyz | gzip > backup_$DATE.sql.gz
```

### Stack Backup

```bash
# Backup stack configuration
tar -czf qenergyz-config-backup.tar.gz docker-stack.yml configs/ secrets.txt
```

### Disaster Recovery

1. **Save stack configuration and data**
2. **Recreate Swarm cluster**
3. **Restore secrets and configs**
4. **Restore data volumes**
5. **Deploy stack**

```bash
# Restore procedure
docker swarm init
docker secret create qenergyz_db_password < secrets/db_password.txt
docker config create nginx_config configs/nginx.conf
docker stack deploy -c docker-stack.yml qenergyz
```

## Troubleshooting

### Common Issues

1. **Service Not Starting**
```bash
docker service ps qenergyz_qenergyz-backend --no-trunc
docker service logs qenergyz_qenergyz-backend
```

2. **Network Issues**
```bash
docker network ls
docker network inspect qenergyz-overlay
```

3. **Node Problems**
```bash
docker node inspect node-name
docker node ls --filter "role=manager"
```

### Health Checks

```yaml
services:
  qenergyz-backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### Performance Optimization

1. **Resource Limits**: Set appropriate CPU and memory limits
2. **Replica Distribution**: Spread replicas across nodes
3. **Network Optimization**: Use overlay networks efficiently
4. **Storage**: Use fast storage for databases

## Migration Guide

### From Docker Compose

1. Update compose file to stack format (version 3.8+)
2. Add deploy sections for services
3. Convert environment files to secrets
4. Update network definitions
5. Test in development environment

### From Kubernetes

1. Map Kubernetes concepts to Swarm:
   - Deployments → Services
   - ConfigMaps → Configs
   - Secrets → Secrets
   - Ingress → External load balancer

2. Recreate resource definitions in stack format
3. Adjust networking and storage configurations

## Best Practices

1. **Use specific image tags** instead of `latest`
2. **Implement health checks** for all services
3. **Set resource limits** to prevent resource contention
4. **Use secrets** for sensitive data
5. **Plan node roles** carefully
6. **Monitor cluster health** continuously
7. **Backup regularly** and test recovery procedures
8. **Update services** using rolling updates
9. **Use external storage** for production data
10. **Document your deployment** thoroughly

## Support and Resources

- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [Docker Stack Deploy Reference](https://docs.docker.com/engine/reference/commandline/stack_deploy/)
- [Production Swarm Best Practices](https://docs.docker.com/engine/swarm/admin_guide/)

For Qenergyz-specific deployment issues:
- Check service logs first
- Verify secrets and configs
- Monitor resource usage
- Contact support with deployment details