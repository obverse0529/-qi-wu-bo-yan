# 开发指南

## 环境准备

### 必要工具

- Python 3.11+
- Node.js 18+
- Git
- Docker Desktop

### 1. 克隆项目

```bash
git clone <repo-url>
cd qi_wu_bo_yan
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

关键配置项：
- `DATABASE_URL`: PostgreSQL 连接字符串
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j 连接
- `MILVUS_HOST`, `MILVUS_PORT`: Milvus 连接
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`: MinIO 连接

### 3. 启动中间件

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

这将启动：
- PostgreSQL (:5432)
- Neo4j (:7474, :7687)
- Milvus (:9091)
- MinIO (:9000, :9001)
- Redis (:6379)
- Nginx (:80)

### 4. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 5. 初始化数据库

```bash
python ../scripts/init_db.py
```

### 6. 启动后端

```bash
uvicorn app.main:app --reload --port 8000
```

### 7. 启动前端

```bash
cd frontend
npm install
npm run dev
```

---

## 项目结构详解

### 后端 (backend/)

```
backend/
├── app/
│   ├── api/v1/           # API 路由
│   │   ├── artifacts.py  # 文物 CRUD
│   │   ├── images.py     # 图像上传
│   │   ├── reconstruct.py # 3D重建
│   │   ├── stories.py    # 故事生成
│   │   └── kg.py         # 知识图谱
│   │
│   ├── core/             # 核心配置
│   │   ├── config.py     # Pydantic 设置
│   │   ├── database.py   # 数据库连接
│   │   └── security.py   # 安全相关
│   │
│   ├── models/           # SQLAlchemy 模型
│   │   ├── artifact.py   # 文物相关模型
│   │   └── schemas.py   # Pydantic schemas
│   │
│   ├── services/         # 业务逻辑
│   │   ├── hunyuan3d_service.py
│   │   ├── gemma_service.py
│   │   ├── rag_service.py
│   │   └── kg_service.py
│   │
│   └── main.py          # FastAPI 应用入口
│
├── requirements.txt
└── pyproject.toml
```

### 前端 (frontend/)

```
frontend/
├── src/
│   ├── components/       # React 组件
│   │   ├── ModelViewer/ # 3D 查看器
│   │   ├── ImageUpload/ # 图像上传
│   │   └── ...
│   │
│   ├── pages/          # 页面组件
│   │   ├── Home.tsx
│   │   ├── Gallery.tsx
│   │   ├── Upload.tsx
│   │   ├── Viewer.tsx
│   │   ├── Story.tsx
│   │   └── Admin.tsx
│   │
│   ├── services/       # API 调用
│   │   ├── api.ts      # API 客户端
│   │   └── ws.ts       # WebSocket
│   │
│   ├── types/          # TypeScript 类型
│   └── utils/          # 工具函数
│
├── package.json
└── vite.config.ts
```

### 脚本 (scripts/)

```
scripts/
├── init_db.py           # 初始化数据库
├── init_services.py     # 初始化服务连接
├── train_hunyuan3d.py   # Hunyuan3D 微调
├── train_gemma.py       # Gemma 微调
├── import_artifacts.py  # 批量导入文物
├── process_images.py    # 图像预处理
└── utils/              # 共享工具
    └── cloud_utils.py
```

---

## 添加新功能

### 添加新的 API 端点

1. 在 `backend/app/api/v1/` 创建新文件：

```python
# backend/app/api/v1/new_feature.py
from fastapi import APIRouter, Depends
router = APIRouter()

@router.get("/items")
async def list_items():
    return {"items": []}
```

2. 在 `backend/app/main.py` 注册路由：

```python
from app.api.v1 import new_feature
app.include_router(new_feature.router, prefix="/api/v1")
```

### 添加新的数据模型

1. 在 `backend/app/models/artifact.py` 添加 SQLAlchemy 模型：

```python
class NewModel(Base):
    __tablename__ = "new_table"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255))
```

2. 在 `backend/app/models/schemas.py` 添加 Pydantic schema：

```python
class NewModelSchema(BaseModel):
    id: UUID
    name: str
```

### 添加新的前端页面

1. 在 `frontend/src/pages/` 创建页面组件
2. 在 `frontend/src/App.tsx` 添加路由：

```tsx
import { NewPage } from './pages/NewPage';

<Route path="/new-page" element={<NewPage />} />
```

---

## 测试

### 后端测试

```bash
cd backend
pytest tests/ -v
```

### 前端测试

```bash
cd frontend
npm test
```

### 集成测试

```bash
# 启动完整环境后
python scripts/import_artifacts.py --check --source dataset/sample_artifacts.json
```

---

## 常见问题

### 1. 数据库连接失败

检查 PostgreSQL 是否启动：
```bash
docker ps | grep postgres
```

尝试重新连接：
```bash
psql -h localhost -U postgres -d qi_wu_bo_yan
```

### 2. 模型加载失败

确保模型文件存在：
```bash
ls -la models/hunyuan3d_finetuned/
ls -la models/gemma3_artifact_story_finetuned/
```

### 3. 图像上传失败

检查 MinIO 服务：
```bash
docker ps | grep minio
```

检查存储目录权限：
```bash
chmod 755 dataset/raw
```

### 4. 前端构建失败

清除缓存重试：
```bash
cd frontend
rm -rf node_modules dist
npm install
```

---

## 代码规范

### Python

- 使用 type hints
- 遵循 PEP 8
- 使用 dataclass 管理配置
- 异步优先（async/await）

### TypeScript

- 启用严格模式
- 使用接口而非类型别名
- 组件使用函数式组件
- 使用 TanStack Query 管理数据获取

### Git 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
test: 测试
chore: 构建/工具
```

示例：
```bash
git commit -m "feat: 添加文物3D预览功能"
git commit -m "fix: 修复图像上传进度条不更新问题"
```
