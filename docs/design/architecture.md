# 系统架构设计

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端 (React)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │ Upload  │ │ Viewer  │ │ Gallery │ │ Story   │ │ Admin   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │ REST API / WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                        API 网关 (FastAPI)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │Artifact │ │ Image   │ │Reconstruct│ │ Story  │ │   KG    │ │
│  │ CRUD    │ │ Upload  │ │  Task   │ │Generate │ │ Query   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                          服务层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Hunyuan3D    │  │ Gemma3 LLM   │  │ RAG Service  │          │
│  │ Service       │  │ Service      │  │ (Milvus)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                              │                                   │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Knowledge     │  │ MinIO        │                            │
│  │ Graph        │  │ Storage       │                            │
│  │ (Neo4j)      │  │              │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       数据层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ PostgreSQL   │  │   Milvus     │  │    Neo4j    │          │
│  │ (主数据库)    │  │ (向量数据库)  │  │ (知识图谱)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 核心流程

### 3D重建流程

```
用户上传多视图图像
        │
        ▼
┌─────────────────┐
│  图像预处理      │  ← Hunyuan3DService.preprocess_image()
│  (尺寸标准化)    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  3D重建推理     │  ← Hunyuan3DService.reconstruct()
│  (多视图融合)    │
└─────────────────┘
        │
        ├──→ GLB模型文件 → MinIO存储
        │
        ▼
┌─────────────────┐
│  生成缩略图     │  ← 用于前端预览
└─────────────────┘
        │
        ▼
    更新任务状态
```

### 文物故事生成流程

```
用户请求生成故事
        │
        ▼
┌─────────────────┐
│  RAG检索        │  ← RAGService.search()
│  (相似文档)     │     查询与文物相关的历史文档
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Prompt构建     │  ← 构建包含文物信息和检索结果的Prompt
│                 │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Gemma3推理     │  ← GemmaService.generate_artifact_story()
│  (故事生成)     │
└─────────────────┘
        │
        ├──→ 故事文本 → PostgreSQL存储
        │
        ▼
    更新任务状态
```

## 数据模型

### 核心实体关系

```
Artifact (文物)
    │
    ├── ArtifactImage (文物图像)  1:N
    │
    ├── ArtifactModel (3D模型)   1:N
    │
    ├── ArtifactStory (文物故事) 1:N
    │
    └── ReconstructionTask (重建任务) 1:N
```

### PostgreSQL 表结构

**artifacts**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR | 文物名称 |
| dynasty | VARCHAR | 朝代 |
| category | VARCHAR | 分类 |
| site | VARCHAR | 出土地点 |
| materials | TEXT | 材质 |
| techniques | TEXT | 工艺 |
| description | TEXT | 描述 |
| provenance | TEXT | 出土情况 |
| era | VARCHAR | 时期 |
| created_at | TIMESTAMP | 创建时间 |

**artifact_images**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| artifact_id | UUID | 外键 |
| view_type | VARCHAR | 视图类型 |
| file_path | TEXT | 文件路径 |
| file_url | TEXT | 访问URL |

**artifact_models**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| artifact_id | UUID | 外键 |
| model_url | TEXT | 模型URL |
| file_path | TEXT | 文件路径 |
| polygon_count | INTEGER | 多边形数 |
| has_texture | BOOLEAN | 是否有纹理 |
| file_size | BIGINT | 文件大小 |

**reconstruction_tasks**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| artifact_id | UUID | 外键 |
| status | VARCHAR | 状态 |
| progress | INTEGER | 进度% |
| model_id | UUID | 关联模型 |

### Milvus Collection Schema

```python
Collection: "artifact_documents"
Fields:
  - id: VARCHAR (primary key)
  - artifact_id: VARCHAR
  - artifact_name: VARCHAR
  - content: VARCHAR (65535)
  - source: VARCHAR
  - source_type: VARCHAR
  - page: INT32
  - year: INT32
  - vector: FLOAT_VECTOR (embedding_dim)
```

### Neo4j Graph Schema

**节点类型**
- Artifact: 文物
- Dynasty: 朝代
- Category: 分类
- Site: 地点
- Technique: 工艺
- Material: 材质
- Museum: 博物馆

**关系类型**
- BELONGS_TO_DYNASTY: 属于朝代
- CATEGORY_IS: 分类为
- EXCAVATED_FROM: 出土于
- MADE_USING: 采用工艺
- MADE_OF: 材质为
- COLLECTED_BY: 被收藏
- RELATED_TO: 相关
- SIMILAR_TO: 相似

## 部署架构

### 开发环境
- 所有服务本地运行
- Docker Compose 启动中间件
- 前端: Vite Dev Server

### 生产环境建议
```
                    ┌─────────────┐
                    │   Nginx     │
                    │ (反向代理)   │
                    └─────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
    │Frontend  │    │ Backend   │   │  Static   │
    │(CDN)    │    │ (Gunicorn)│   │  Files    │
    └─────────┘    └───────────┘   └───────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
    │Postgres │    │  MinIO    │   │  Redis    │
    └─────────┘    └───────────┘   └───────────┘
         │                │                │
    ┌────▼────┐    ┌─────▼─────┐
    │ Milvus  │    │  Neo4j    │
    └─────────┘    └───────────┘
```

## 性能优化

### 3D模型推理
- 使用混合精度 (BF16)
- 启用梯度检查点节省显存
- 批量处理时使用 gradient accumulation

### LLM推理
- INT4量化减少显存占用
- 启用KV缓存
- 限制最大生成长度

### 图像处理
- 多线程并行处理
- 使用 PIL LANCZOS 重采样
- 按需加载，避免一次性读取全部

### 数据库
- 为高频查询字段建立索引
- 使用连接池复用连接
- 批量插入减少事务开销
