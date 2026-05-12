# 运维手册

> 启物博言智慧博物馆系统 | 版本 1.0

---

## 1. 系统架构速览

```
                     ┌──────────┐
                     │  Nginx   │  :80/:443 (公网入口)
                     └────┬─────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐     ┌─────▼─────┐    ┌────▼─────┐
    │Frontend │     │ Backend   │    │  MinIO   │
    │  :3000  │     │  :8000    │    │  :9000   │
    └─────────┘     └─────┬─────┘    └──────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐
│PostgreSQL│  │   Neo4j    │  │   Milvus     │
│  :5432   │  │:7474/:7687 │  │    :9091     │
└──────────┘  └────────────┘  └──────┬───────┘
                                     │
                               ┌─────▼─────┐
                               │   etcd    │
                               │  :2379    │
                               └───────────┘

   ┌──────────┐
   │  Redis   │
   │  :6379   │
   └──────────┘
```

### 服务清单

| 服务 | 容器 | 端口 | 用途 | 关键性 |
|------|------|------|------|--------|
| Nginx | `nginx` | 80/443 | 反向代理、SSL | 高 |
| Frontend | `frontend` | 3000 | React SPA | 高 |
| Backend | `backend` | 8000 | FastAPI 业务 | 高 |
| PostgreSQL | `postgres` | 5432 | 主数据库 | **极高** |
| Neo4j | `neo4j` | 7474/7687 | 知识图谱 | 中 |
| Milvus | `milvus` | 9091 | 向量检索 | 中 |
| etcd | `etcd` | 2379 | Milvus 协调 | 中 |
| MinIO | `minio` | 9000/9001 | 文件存储 | **极高** |
| Redis | `redis` | 6379 | 缓存/限流 | 中 |

---

## 2. 日常运维

### 2.1 每日检查（5 分钟）

```bash
cd /opt/qi-wu-bo-yan

# 所有容器状态
docker compose -f docker/docker-compose.yml ps

# 异常容器
docker compose -f docker/docker-compose.yml ps --filter "health=unhealthy"

# 磁盘使用
df -h / /opt/backups

# 内存使用
free -h
```

### 2.2 日志巡检

```bash
# 错误日志（最近 1 小时）
docker compose -f docker/docker-compose.yml logs --since 1h backend | grep -i error

# Nginx 访问量（最近 1 小时）
docker compose exec nginx cat /var/log/nginx/access.log | wc -l

# 异常 HTTP 状态码
docker compose exec nginx cat /var/log/nginx/access.log | grep -E ' (50[0-9]|40[3-9]) '
```

### 2.3 容器重启

```bash
# 重启单个服务（不影响其他）
docker compose -f docker/docker-compose.yml restart backend
docker compose -f docker/docker-compose.yml restart nginx

# 全部重启（几秒中断）
docker compose -f docker/docker-compose.yml restart
```

### 2.4 清理磁盘

```bash
# Docker 缓存和未使用镜像
docker system prune -f

# 旧备份文件
find /opt/backups -mtime +30 -delete
```

---

## 3. 监控告警

### 3.0 Prometheus 指标（推荐）

后端暴露 `/metrics` 端点（Prometheus 格式），可集成 Prometheus + Grafana：

```bash
# 验证指标端点
curl http://localhost:8000/metrics
```

**Prometheus 配置示例** (`prometheus.yml`)：

```yaml
scrape_configs:
  - job_name: qiwu-backend
    scrape_interval: 15s
    static_configs:
      - targets: ["backend:8000"]
    metrics_path: /metrics
```

**关键指标**：
| 指标 | 说明 |
|------|------|
| `http_requests_total` | API 请求总数 |
| `http_request_duration_seconds` | 请求延迟分布 |
| `http_requests_in_flight` | 当前并发请求数 |
| `db_connections_active` | 活跃数据库连接数 |
| `cache_hit_ratio` | Redis 缓存命中率 |

**健康检查端点**：
| 端点 | 用途 |
|------|------|
| `GET /health` | 基本健康状态 |
| `GET /api/v1/health` | API 层健康检查 |
| `GET /health/detailed` | 详细健康（含各服务状态） |

### 3.1 简易监控脚本

创建 `/opt/qi-wu-bo-yan/scripts/health_check.sh`：

```bash
#!/bin/bash
# 健康检查 + 异常告警

HEALTHY=$(docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml ps --filter "health=unhealthy" --format '{{.Name}}')

if [ -n "$HEALTHY" ]; then
    echo "[$(date)] 异常容器: $HEALTHY" | tee -a /var/log/qiwu-alert.log
    # 可选：发送通知
    # curl -X POST -d "text=异常容器: $HEALTHY" <webhook_url>
fi

# 磁盘告警
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "[$(date)] 磁盘使用率: ${DISK_USAGE}%" | tee -a /var/log/qiwu-alert.log
fi

# 内存告警
MEM_AVAIL=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAIL" -lt 2048 ]; then
    echo "[$(date)] 可用内存不足: ${MEM_AVAIL}MB" | tee -a /var/log/qiwu-alert.log
fi
```

### 3.2 配置 crontab 定时检查

```bash
chmod +x /opt/qi-wu-bo-yan/scripts/health_check.sh
sudo crontab -e
```

```
# 每 5 分钟健康检查
*/5 * * * * /opt/qi-wu-bo-yan/scripts/health_check.sh
```

### 3.3 关键告警阈值

| 指标 | 警告 | 严重 |
|------|------|------|
| 容器健康状态 | 任一 unhealthy | 多个 unhealthy |
| 磁盘使用率 | > 80% | > 90% |
| 可用内存 | < 2GB | < 1GB |
| Backend 响应时间 | > 1s | > 3s |
| PostgreSQL 连接数 | > 60 | > 90 |
| Nginx 5xx 率 | > 1% | > 5% |

---

## 4. 故障恢复

### 4.1 服务不健康

**症状**：`docker compose ps` 显示 `unhealthy`

```bash
# 1. 查看日志定位原因
docker compose -f docker/docker-compose.yml logs <service_name> --tail=100

# 2. 尝试重启
docker compose restart <service_name>

# 3. 如果重启无效，重建容器
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --force-recreate <service_name>
```

### 4.2 PostgreSQL 无法启动

**症状**：PostgreSQL 容器反复退出

```bash
# 查看详细日志
docker compose logs postgres --tail=50

# 常见原因 1：磁盘满
df -h /var/lib/docker/volumes

# 常见原因 2：数据损坏
# 从备份恢复（见部署文档 6.4）
```

### 4.3 后端 500 错误

**症状**：API 返回 500 Internal Server Error

```bash
# 查看后端日志
docker compose logs backend --tail=200 | grep -A5 ERROR

# 检查数据库连接
docker compose exec backend python -c "
from app.core.config import settings
import asyncpg
import asyncio
async def check():
    conn = await asyncpg.connect(settings.database_url.replace('+asyncpg', ''))
    print(await conn.fetchval('SELECT 1'))
    await conn.close()
asyncio.run(check())
"

# 如果需要回滚最近部署
git log --oneline -5
git revert <bad_commit_hash>
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
```

### 4.4 内存溢出（OOM）

**症状**：容器突然退出，日志含 `OOMKilled` 字样

```bash
# 确认
docker inspect <container> | grep -i oom

# 临时方案：增加内存限制
# 编辑 docker/docker-compose.prod.yml 调整对应服务的 memory limits

# 永久方案：降低服务并发数
# backend: 减少 --workers 数量
```

### 4.5 GPU 不可用

**症状**：LLM/3D 推理失败

```bash
# 检查 GPU 状态
nvidia-smi

# 如果没有 GPU，切换为 CPU 模式
# 编辑 docker/.env.docker.local:
#   GEMMA_DEVICE=cpu
#   HUNYAN3D_DEVICE=cpu

# 重启 backend
docker compose restart backend
```

### 4.6 磁盘满应急处理

```bash
# 快速清理
docker system prune -af --volumes  # 警告：删除未使用卷
docker compose down && docker compose up -d

# 如果仍然不足
du -sh /var/lib/docker/volumes/* | sort -rh | head -5
# 确认哪些卷占空间最大，清理对应旧数据
```

---

## 5. 备份恢复实操

### 5.1 紧急全量备份

```bash
#!/bin/bash
# 紧急全量备份（故障前执行）
BACKUP_ROOT="/opt/backups/emergency_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_ROOT"

# PostgreSQL
docker compose -f /opt/qi-wu-bo-yan/docker/docker-compose.yml exec -T postgres \
  pg_dumpall -U postgres > "$BACKUP_ROOT/postgres_full.sql"

# MinIO
docker compose exec -T minio mc mirror /data "$BACKUP_ROOT/minio"

# Neo4j
docker compose exec -T neo4j neo4j-admin dump --to=- > "$BACKUP_ROOT/neo4j.dump"

echo "急备份完成: $BACKUP_ROOT"
```

### 5.2 灾难恢复

```bash
# 1. 停止所有服务
cd /opt/qi-wu-bo-yan
docker compose -f docker/docker-compose.yml down

# 2. 清空数据卷（危险操作！）
docker volume rm qi-wu-bo-yan_postgres_data
docker volume rm qi-wu-bo-yan_minio_data
docker volume rm qi-wu-bo-yan_neo4j_data

# 3. 重新启动（创建空卷）
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d postgres minio neo4j

# 4. 恢复 PostgreSQL
docker compose exec -T postgres psql -U postgres < /opt/backups/emergency_*/postgres_full.sql

# 5. 恢复 MinIO
docker compose exec -T minio mc mirror /opt/backups/emergency_*/minio /data

# 6. 启动全部服务
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

---

## 6. 性能调优

### 6.1 后端并发调优

修改 `docker/docker-compose.prod.yml` 中 backend 的 `--workers`：

```
CPU 核心数   → workers 建议值
2 核        → 2
4 核        → 4
8 核        → 6
16 核       → 8
```

### 6.2 PostgreSQL 调优

通过环境变量调整连接池：

```ini
# docker/.env.docker.local
# 增加 max_connections（默认 100）
POSTGRES_MAX_CONNECTIONS=200
```

### 6.3 Milvus 调优

```ini
# 增加 Milvus 内存限制（docker-compose.prod.yml）
milvus:
  deploy:
    resources:
      limits:
        memory: 12G
```

---

## 7. 常用命令速查

```bash
# === 状态 ===
docker compose -f docker/docker-compose.yml ps                    # 所有容器状态
docker compose -f docker/docker-compose.yml logs --tail=50 -f     # 实时日志
docker stats --no-stream                                          # 资源使用

# === 启停 ===
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d     # 启动
docker compose -f docker/docker-compose.yml down                                        # 停止
docker compose restart <service>                                                         # 重启

# === 数据库 ===
docker compose exec postgres psql -U postgres -d qiwu                                   # PostgreSQL CLI
docker compose exec postgres pg_dump -U postgres -d qiwu -Fc > backup.dump              # 导出
docker compose exec redis redis-cli                                                      # Redis CLI

# === 诊断 ===
docker compose exec backend python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"  # 检查数据库连接
docker compose exec nginx nginx -t                                                                                    # 检查 Nginx 配置
curl -s http://localhost:8000/api/v1/health                                                                            # 后端健康检查

# === 更新 ===
git pull && docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build

# === 清理 ===
docker system prune -f                    # Docker 缓存
docker compose logs --tail=0 -f           # 清空日志（重新 follow）
```

---

*手册版本: 1.0 | 适用系统: 启物博言 v1.0.0*
