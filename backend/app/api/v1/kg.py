from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.models.artifact import Artifact
from app.models.schemas import KGQueryResponse, KGNode, KGEdge, RelatedArtifact
from app.services.kg_service import get_kg_service, init_kg_service

router = APIRouter()


@router.get("/kg/query", response_model=KGQueryResponse)
async def query_knowledge_graph(
    artifact_id: str = Query(..., description="文物ID"),
    depth: int = Query(2, ge=1, le=5, description="查询深度"),
    db: AsyncSession = Depends(get_db),
):
    """
    查询文物知识图谱信息

    从 Neo4j 获取文物的图谱结构，包括关联的朝代、分类、工艺等信息
    """
    try:
        kg_service = get_kg_service()

        # 确保连接
        if not kg_service._connected:
            if not kg_service.connect():
                raise HTTPException(status_code=503, detail="知识图谱服务不可用")

        # 查询图谱
        graph_data = kg_service.query_artifact_graph(artifact_id, depth)

        # 转换格式
        nodes = [
            KGNode(
                id=n.get("id", ""),
                label=n.get("label", "Unknown"),
                properties=n.get("properties", {}),
            )
            for n in graph_data.get("nodes", [])
        ]

        edges = [
            KGEdge(
                source=e.get("source", ""),
                target=e.get("target", ""),
                type=e.get("type", ""),
                properties=e.get("properties", {}),
            )
            for e in graph_data.get("edges", [])
        ]

        return KGQueryResponse(nodes=nodes, edges=edges)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识图谱查询失败: {str(e)}")


@router.get("/kg/search", response_model=list[dict])
async def search_knowledge_graph(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
):
    """
    知识图谱语义搜索

    通过关键词搜索匹配的节点（文物、朝代、工艺等）
    """
    try:
        kg_service = get_kg_service()

        if not kg_service._connected:
            if not kg_service.connect():
                raise HTTPException(status_code=503, detail="知识图谱服务不可用")

        results = kg_service.search_by_keyword(keyword)

        return [
            {
                "id": r.get("id", ""),
                "name": r.get("name", ""),
                "type": r.get("label", ""),
                "dynasty": r.get("dynasty"),
                "category": r.get("category"),
                "connections": r.get("degree", 0),
            }
            for r in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识图谱搜索失败: {str(e)}")


@router.get("/kg/related/{artifact_id}", response_model=list[RelatedArtifact])
async def get_related_artifacts(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    获取相关文物推荐

    基于图谱关系查找相似文物（同朝代、同类型、相同工艺等）
    """
    try:
        kg_service = get_kg_service()

        if not kg_service._connected:
            if not kg_service.connect():
                raise HTTPException(status_code=503, detail="知识图谱服务不可用")

        related = kg_service.search_related_artifacts(str(artifact_id))

        return [
            RelatedArtifact(
                artifact_id=r["artifact_id"],
                artifact_name=r["name"],
                relationship=r.get("relationship", "RELATED"),
                dynasty=r.get("dynasty"),
                category=r.get("category"),
            )
            for r in related
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取相关文物失败: {str(e)}")


@router.post("/kg/init")
async def initialize_knowledge_graph(
    db: AsyncSession = Depends(get_db),
):
    """
    初始化知识图谱

    从现有文物数据构建图谱关系
    """
    try:
        kg_service = get_kg_service()

        # 确保连接
        if not kg_service._connected:
            if not kg_service.connect():
                return {"message": "无法连接到Neo4j", "status": "failed"}

        # 获取所有文物
        from sqlalchemy import select
        query = select(Artifact)
        result = await db.execute(query)
        artifacts = result.scalars().all()

        success_count = 0
        for artifact in artifacts:
            try:
                # 从 extra_data 中提取更多信息
                metadata = artifact.extra_data or {}
                techniques = metadata.get("techniques", [])
                materials = metadata.get("materials", [])
                site = metadata.get("site")

                # 构建图谱
                kg_service.build_from_artifact_data(
                    artifact_id=str(artifact.id),
                    name=artifact.name,
                    dynasty=artifact.dynasty or "",
                    category=artifact.category or "",
                    site=site,
                    techniques=techniques if isinstance(techniques, list) else [],
                    materials=materials if isinstance(materials, list) else [],
                )
                success_count += 1
            except Exception as e:
                print(f"构建文物图谱失败 {artifact.id}: {e}")

        return {
            "message": f"成功构建 {success_count}/{len(artifacts)} 个文物图谱",
            "status": "success",
            "total": len(artifacts),
            "success": success_count,
        }

    except Exception as e:
        return {"message": f"初始化失败: {str(e)}", "status": "failed"}


@router.post("/kg/connect")
async def connect_kg_service():
    """连接知识图谱服务"""
    try:
        kg_service = get_kg_service()
        success = kg_service.connect()

        if success:
            return {"message": "连接成功", "status": "connected"}
        else:
            return {"message": "连接失败", "status": "failed"}

    except Exception as e:
        return {"message": f"连接异常: {str(e)}", "status": "error"}


@router.get("/kg/stats")
async def get_kg_stats():
    """获取知识图谱统计信息"""
    try:
        kg_service = get_kg_service()

        if not kg_service._connected:
            if not kg_service.connect():
                return {"status": "disconnected"}

        stats = kg_service.get_statistics()
        return {
            "status": "connected",
            "statistics": stats,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/kg/artifact/{artifact_id}")
async def delete_artifact_from_kg(artifact_id: UUID):
    """从知识图谱删除文物"""
    try:
        kg_service = get_kg_service()

        if not kg_service._connected:
            if not kg_service.connect():
                raise HTTPException(status_code=503, detail="知识图谱服务不可用")

        success = kg_service.delete_artifact(str(artifact_id))

        if success:
            return {"message": "删除成功", "artifact_id": str(artifact_id)}
        else:
            return {"message": "删除失败或节点不存在", "artifact_id": str(artifact_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
