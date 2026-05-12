# 生产环境部署文档

> 启物博言智慧博物馆系统 v1.0.0  
> 最后更新: 2026-05-12

---

## 1. 服务器要求

### 最低配置

| 资源 | 开发/测试 | 生产环境 |
|------|-----------|----------|
| CPU | 4 核 | 8 核以上 |
| 内存 | 16 GB | 32 GB 以上 |
| 磁盘 | 50 GB SSD | 200 GB SSD 以上 |
| GPU | 可选 | 推荐 NVIDIA RTX 3080+ (≥10GB VRAM) |
| 操作系统 | Ubuntu 22.04+ / Debian 12+ | Ubuntu 22.04 LTS |

### 端口规划

| 端口 | 服务 | 对外暴露 |
|------|------|----------|
| 80 | Nginx HTTP | ✅ 是 |
| 443 | Nginx HTTPS | ✅ 是 |
| 5432 | PostgreSQL | ❌ 仅内网 |
| 7474 | Neo4j HTTP | ❌ 仅内网 |
| 7687 | Neo4j Bolt | ❌ 仅内网 |
| 9091 | Milvus | ❌ 仅内网 |
| 9000 | MinIO API | ❌ 仅内网 |
| 9001 | MinIO Console | ❌ 仅内网 |
| 6379 | Redis | ❌ 仅内网 |
| 8000 | Backend | ❌ 仅内网 |

---

## 2. 环境准备

### 2.1 安装 Docker

```bash
# 卸载旧版本
sudo apt-get remove docker docker-engine docker.io containerd runc

# 安装依赖
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine + Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2.2 验证安装

```bash
docker --version          # ≥ 24.0
docker compose version    # ≥ 2.20
```

### 2.3 配置 Docker（生产建议）

```bash
# 配置 Docker daemon
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}
EOF

sudo systemctl restart docker
```

### 2.4 拉取项目

```bash
git clone https://github.com/obverse0529/-qi-wu-bo-yan.git /opt/qi-wu-bo-yan
cd /opt/qi-wu-bo-yan
```

---

## 3. 配置

### 3.1 创建生产环境变量

```bash
# 复制模板
cp docker/.env.docker docker/.env.docker.local

# 生成随机密码
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" >> docker/.env.docker.local
echo "NEO4J_PASSWORD=$(openssl rand -base64 24)" >> docker/.env.docker.local
echo "MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)" >> docker/.env.docker.local
```

### 3.2 必须修改的变量

编辑 `docker/.env.docker.local`，确认以下变量：

```ini
# ---- 必须修改 ----
POSTGRES_PASSWORD=<强密码>
NEO4J_AUTH=neo4j/<强密码>
MINIO_ROOT_PASSWORD=<强密码>

# ---- 按需修改 ----
APP_DEBUG=false
CORS_ORIGINS=["https://your-domain.com"]

# ---- GPU 相关（无 GPU 则忽略）----
GEMMA_DEVICE=cuda          # 无 GPU 改为 cpu
```

### 3.3 检查清单

- [ ] 所有默认密码已更换
- [ ] `APP_DEBUG=false`
- [ ] `CORS_ORIGINS` 包含实际域名
- [ ] `.env.docker.local` 未提交到 Git

---

## 4. 部署

### 4.1 快速部署（Docker Compose）

```bash
cd /opt/qi-wu-bo-yan

# 启动所有服务（后台运行）
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file docker/.env.docker.local up -d

# 查看启动状态
docker compose ps

# 查看日志
docker compose logs -f --tail=50
```

### 4.2 等待健康检查通过

```bash
# 等待所有服务 healthy
watch docker compose ps

# 预期输出：所有服务 State 列为 "Up (healthy)"
```

整个过程约 1-3 分钟（首次拉取镜像可能需要更久）。

### 4.3 验证部署

```bash
# 后端健康检查
curl http://localhost:8000/api/v1/health

# 数据库连接
docker compose exec postgres pg_isready -U postgres -d qiwu

# Neo4j
curl http://localhost:7474

# MinIO
curl http://localhost:9000/minio/health/live
```

---

## 5. Nginx 反向代理

### 5.1 HTTPS 证书（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install -y certbot

# 获取证书（standalone 模式，需先停止 nginx）
docker compose stop nginx
sudo certbot certonly --standalone -d your-domain.com
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d nginx
```

### 5.2 启用 HTTPS

1. 创建 SSL 目录：
```bash
mkdir -p docker/ssl
```

2. 复制证书：
```bash
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem docker/ssl/
sudo chmod 644 docker/ssl/*
```

3. 编辑 `docker/nginx.conf`，取消 HTTPS server 块注释，修改 `server_name`。

4. 重载 Nginx：
```bash
docker compose exec nginx nginx -s reload
```

### 5.3 证书自动续期

```bash
# 添加 crontab（每月 1 号凌晨续期）
sudo crontab -e
# 添加：
0 2 1 * * certbot renew --quiet --pre-hook "docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml stop nginx" --post-hook "cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/qi-wu-bo-yan/docker/ssl/ && cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/qi-wu-bo-yan/docker/ssl/ && docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml -f /opt/qi-wu-bo-yan/docker/docker-compose.prod.yml up -d nginx"
```

---

## 6. 备份策略

### 6.1 PostgreSQL 备份

```bash
# 创建备份脚本
cat > /opt/qi-wu-bo-yan/scripts/backup_postgres.sh <<'SCRIPT'
#!/bin/bash
BACKUP_DIR="/opt/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml exec -T postgres \
  pg_dump -U postgres -d qiwu -Fc > "$BACKUP_DIR/qiwu_$TIMESTAMP.dump"

# 保留最近 7 天
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete
echo "Backup completed: qiwu_$TIMESTAMP.dump"
SCRIPT

chmod +x /opt/qi-wu-bo-yan/scripts/backup_postgres.sh
```

### 6.2 MinIO 备份

```bash
cat > /opt/qi-wu-bo-yan/scripts/backup_minio.sh <<'SCRIPT'
#!/bin/bash
BACKUP_DIR="/opt/backups/minio"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml exec -T minio \
  mc mirror --overwrite /data "$BACKUP_DIR/minio_$TIMESTAMP"

find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
echo "MinIO backup completed"
SCRIPT

chmod +x /opt/qi-wu-bo-yan/scripts/backup_minio.sh
```

### 6.3 备份时间表

```bash
# 添加 crontab
sudo crontab -e
```

```
# 每天凌晨 2 点备份 PostgreSQL
0 2 * * * /opt/qi-wu-bo-yan/scripts/backup_postgres.sh >> /var/log/qiwu-backup.log 2>&1

# 每周日凌晨 4 点备份 MinIO
0 4 * * 0 /opt/qi-wu-bo-yan/scripts/backup_minio.sh >> /var/log/qiwu-backup.log 2>&1
```

### 6.4 恢复

```bash
# PostgreSQL 恢复
docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml exec -T postgres \
  pg_restore -U postgres -d qiwu --clean --if-exists < /opt/backups/postgres/qiwu_YYYYMMDD_HHMMSS.dump

# MinIO 恢复
docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml exec -T minio \
  mc mirror /backup_path /data
```

---

## 7. 监控

### 7.1 容器状态监控

```bash
# 检查所有容器状态
docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml ps

# 资源使用
docker stats --no-stream
```

### 7.2 关键指标

| 指标 | 正常范围 | 告警阈值 |
|------|----------|----------|
| Backend 响应时间 p95 | < 500ms | > 2s |
| PostgreSQL 连接数 | < 50 | > 80 |
| Neo4j 内存 | < 3GB | > 3.5GB |
| Milvus 内存 | < 6GB | > 7GB |
| 磁盘使用率 | < 70% | > 85% |
| GPU 显存 (如有) | < 80% | > 90% |

### 7.3 日志查看

```bash
# 所有服务日志
docker compose -f docker/docker-compose.yml logs -f --tail=100

# 单个服务
docker compose -f docker/docker-compose.yml logs -f backend

# Nginx 访问日志
docker compose exec nginx tail -f /var/log/nginx/access.log
```

---

## 8. 日常运维

### 8.1 启动 / 停止

```bash
# 停止所有服务
docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml -f /opt/qi-wu-bo-yan/docker/docker-compose.prod.yml down

# 启动（保留数据）
docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml -f /opt/qi-wu-bo-yan/docker/docker-compose.prod.yml up -d

# 重启单个服务
docker compose restart backend
```

### 8.2 更新部署

```bash
cd /opt/qi-wu-bo-yan
git pull

# 重新构建并部署（不丢数据）
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build

# 清理旧镜像
docker image prune -f
```

### 8.3 扩容考虑

当并发量增大时：
- 前端：通过 CDN 缓存静态资源
- 后端：增加 uvicorn workers 数量（修改 `docker-compose.prod.yml` 中后端 command 的 `--workers` 参数）
- 数据库：迁移到托管服务（云数据库）

---

## 9. 故障排查

### 问题：容器无法启动

```bash
# 检查详细日志
docker compose logs <service_name>

# 检查端口冲突
sudo lsof -i :<port>

# 检查磁盘空间
df -h
```

### 问题：数据库连接失败

```bash
# 检查 PostgreSQL 健康状态
docker compose exec postgres pg_isready -U postgres -d qiwu

# 检查连接字符串（容器内使用服务名，非 localhost）
docker compose exec backend env | grep DATABASE_URL
```

### 问题：GPU 不可用

```bash
# 检查 nvidia 驱动
nvidia-smi

# 修改 .env.docker.local
GEMMA_DEVICE=cpu
```

### 问题：内存不足

```bash
# 查看内存使用
free -h
docker stats --no-stream

# 降低 docker-compose.prod.yml 中各服务的 memory limits
```

### 问题：磁盘空间不足

```bash
# 清理 Docker
docker system prune -af --volumes

# 清理旧备份
ls -lh /opt/backups/
```

---

## 10. 安全建议

1. **防火墙** — 仅开放 80/443 端口给公网，使用 ufw：
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 22/tcp    # SSH
   sudo ufw enable
   ```

2. **SSH 加固** — 禁用密码登录，使用密钥认证：
   ```bash
   sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
   sudo systemctl restart sshd
   ```

3. **自动安全更新**：
   ```bash
   sudo apt-get install -y unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

4. **定期审计日志** — 关注 `/var/log/nginx/access.log` 中的异常请求。

---

*文档版本: 1.0 | 适用系统版本: 启物博言 v1.0.0*
