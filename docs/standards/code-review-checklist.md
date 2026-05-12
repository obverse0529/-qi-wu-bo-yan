# 代码审查清单

> 启物博言项目 | 版本 1.0 | 2026-05-12

---

## 通用（所有 PR 必须通过）

### 基本检查
- [ ] 代码已通过 CI 流水线（lint + type check + build）
- [ ] 无遗留的 `console.log`、`print()`、`TODO` 注释
- [ ] 无硬编码的密码、密钥、IP 地址
- [ ] 无被注释掉的代码块（删掉即可，Git 历史可追溯）
- [ ] 无超大文件（图片/模型文件应使用外部存储）
- [ ] PR 描述清楚说明了变更原因和影响范围

### 命名规范
- [ ] 文件名：前端 PascalCase（组件）/ camelCase（工具），后端 snake_case
- [ ] 变量/函数名具有自解释性，不需要注释就能看懂
- [ ] 避免缩写，除非是广泛认可的（如 `id`、`url`、`api`）
- [ ] 布尔变量以 `is`/`has`/`should` 开头

### Git 规范
- [ ] Commit message 遵循 `type: description` 格式（中文或英文均可）
- [ ] 一个 commit 只做一件事
- [ ] PR 分支基于最新的 main

---

## 前端（React + TypeScript）

### React 组件
- [ ] 使用函数式组件 + TypeScript 类型标注
- [ ] Props 有明确的 interface/type 定义（非 `any`）
- [ ] 组件职责单一，一个组件不超过 300 行
- [ ] 无重复的 UI 逻辑（提取为自定义 hook 或工具函数）
- [ ] 正确使用 `useMemo` / `useCallback` 避免不必要的重渲染

### 数据获取
- [ ] 使用 TanStack Query（`useQuery` / `useMutation`）管理 API 请求
- [ ] 加载（Loading）和错误（Error）状态都有 UI 处理
- [ ] API 返回的数据类型有完整的 TypeScript 定义

### 样式
- [ ] 优先使用 Tailwind CSS 类名，避免行内 style
- [ ] 响应式设计：mobile-first，覆盖 320px - 1920px
- [ ] 3D 组件（Three.js）需处理加载状态和错误回退

### 性能
- [ ] 路由懒加载（`React.lazy` + `Suspense`）
- [ ] 3D 模型使用渐进式加载策略
- [ ] 图片使用 WebP 格式
- [ ] 列表超过 50 项使用虚拟滚动

---

## 后端（Python + FastAPI）

### API 设计
- [ ] RESTful 命名：名词复数 + 层级资源
- [ ] 所有端点有 Pydantic 请求/响应 schema
- [ ] 错误响应格式统一（`{"detail": "message"}`）
- [ ] 合适的状态码（200/201/400/404/422/500）

### 数据库
- [ ] 包含对应的 Alembic 迁移脚本
- [ ] 查询使用 SQLAlchemy 2.0 风格（非旧式 Query API）
- [ ] 避免 N+1 查询（使用 `selectinload` / `joinedload`）
- [ ] 新字段有适当的索引（高频查询字段）

### 异步
- [ ] 数据库操作用 async（`AsyncSession`）
- [ ] 外部 API 调用使用 `httpx.AsyncClient`
- [ ] 耗时操作放入后台任务（`BackgroundTasks` / Celery）

### 安全
- [ ] 用户输入有 Pydantic 验证
- [ ] 文件上传校验类型和大小
- [ ] SQL 查询使用参数化（ORM 自动处理）
- [ ] 敏感配置从环境变量读取

### 测试
- [ ] 新增 API 端点有对应的 `test_*.py` 文件
- [ ] 关键业务逻辑有单元测试
- [ ] 测试覆盖率不低于现有水平

---

## AI/ML（脚本）

### 训练脚本
- [ ] 超参数可配置（YAML 配置文件，非硬编码）
- [ ] 训练过程有日志记录和 checkpoint 保存
- [ ] 数据加载前检测格式（DPO format vs raw format）
- [ ] GPU 显存不足时有合理的降级策略（BF16 → QLoRA → CPU）

### 评测脚本
- [ ] 指标计算有明确的公式注释
- [ ] 结果可复现（固定随机种子）
- [ ] 评测结果有可视化图表输出

---

## DevOps

### Docker
- [ ] Dockerfile 分离 dev / prod（多阶段构建）
- [ ] 使用非 root 用户运行应用
- [ ] 不将 `.env` / secrets 打包进镜像
- [ ] 生产镜像使用固定版本 tag（非 `latest`）

### CI/CD
- [ ] 新服务加入 docker-compose 配置
- [ ] 新路径加入 CI 检测范围
- [ ] 部署后验证健康检查通过

---

## 审查流程

1. **自查** — 提交 PR 前先对照本清单逐项检查
2. **自动检查** — CI 流水线自动运行 lint + build + test
3. **同行审查** — 至少 1 人 Review 通过后才能合并
4. **合并** — 使用 Squash & Merge，保持 main 分支干净

---

## 常见踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| DPO 训练 OOM | 3B BF16 模型 > 8GB 显存 | 用 QLoRA NF4 量化 |
| 数据格式不匹配 | preferences.jsonl 已有 DPO 格式 | 加载前检测格式 |
| 模型文件损坏 | 下载中断 | 验证 safetensors 大小 |
| Milvus 启动失败 | etcd 或 minio 依赖未就绪 | 确认 depends_on + healthcheck |
| WebSocket 断连 | 无心跳检测 | 加入 ping/pong + 自动重连 |

---

*清单版本: 1.0 | 下次审核: 项目迭代后*
