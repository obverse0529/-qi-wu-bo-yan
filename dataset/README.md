# 数据集目录

## 目录结构

```
dataset/
├── raw/                          # 原始数据
│   └── artifacts/                # 文物原始图像
│       └── artifact_001/        # 按文物ID组织
│           ├── front.png        # 正面视图
│           ├── side_left.png    # 左侧视图
│           ├── side_right.png   # 右侧视图
│           └── back.png         # 背面视图
│
├── processed/                   # 处理后的数据
│   ├── images/                  # 预处理后的图像
│   │   └── artifact_001/
│   │       ├── front.jpg
│   │       ├── side_left.jpg
│   │       ├── side_right.jpg
│   │       └── back.jpg
│   │
│   └── models/                  # 3D重建模型输出
│       └── artifact_001/
│           └── artifact_001.glb
│
├── annotations/                  # 标注数据
│   └── stories/                 # 文物故事标注
│       ├── train.jsonl
│       ├── val.jsonl
│       └── test.jsonl
│
├── sample_artifacts.json         # 示例文物数据（可导入）
└── README.md
```

## 视图类型

每个文物建议包含 **4个以上** 视图：

| 视图类型 | 说明 |
|----------|------|
| front | 正面 |
| side_left | 左侧 |
| side_right | 右侧 |
| back | 背面 |
| top | 顶部（可选） |
| bottom | 底部（可选） |

## 图像要求

### 分辨率
- 最小: 256 × 256 px
- 推荐: 1024 × 1024 px
- 最大: 4096 × 4096 px

### 格式
- 支持: PNG, JPG, JPEG, BMP, WebP
- 推荐: PNG 或高质量 JPG

### 质量
- 纵横比接近 1:1（正方形）
- 光照均匀，无强烈阴影
- 背景简洁，建议纯色或渐变
- 文物主体清晰可见

## 故事数据格式

文物故事数据采用 JSONL 格式（每行一个JSON对象）：

```jsonl
{"artifact_id": "artifact_001", "artifact_name": "青铜鼎", "dynasty": "商", "category": "青铜器", "story": "这是文物故事...", "source": "《文物》2020年第1期"}
{"artifact_id": "artifact_002", "artifact_name": "四羊方尊", "dynasty": "商", "category": "青铜器", "story": "这是文物故事...", "source": "《考古学报》2019年第3期"}
```

## 导入数据

### 方式一：JSON 导入

```bash
python scripts/import_artifacts.py \
    --source dataset/sample_artifacts.json \
    --format json \
    --batch-size 10
```

### 方式二：CSV 导入

CSV 格式：
```csv
artifact_id,name,dynasty,category,site,materials,techniques,description
artifact_001,青铜鼎,商,青铜器,安阳,青铜,铸造,这是...
```

```bash
python scripts/import_artifacts.py \
    --source dataset/artifacts.csv \
    --format csv \
    --batch-size 10
```

### 检查导入状态

```bash
python scripts/import_artifacts.py --check --source dataset/sample_artifacts.json
```

## 图像处理

### 检查图像质量

```bash
python scripts/process_images.py --check-quality dataset/raw
```

### 批量处理图像

```bash
python scripts/process_images.py \
    --input dataset/raw \
    --output dataset/processed/images \
    --augment \
    --quality 95
```

处理后会自动生成 `processing_report.json` 报告。

## 图像增强

启用 `--augment` 参数时，图像会经过：
1. 尺寸调整（填充至正方形）
2. 对比度增强 (+10%)
3. 色彩增强 (+5%)
4. 锐化 (+10%)

## 统计信息

查看数据集统计：

```python
from app.core.database import AsyncSessionLocal
from app.models.artifact import Artifact, ArtifactImage
from sqlalchemy import select, func

async def stats():
    async with AsyncSessionLocal() as db:
        # 文物总数
        count_query = select(func.count()).select_from(Artifact)
        result = await db.execute(count_query)
        print(f"文物总数: {result.scalar()}")

        # 图像总数
        img_query = select(func.count()).select_from(ArtifactImage)
        result = await db.execute(img_query)
        print(f"图像总数: {result.scalar()}")
```
