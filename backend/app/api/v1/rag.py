from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from uuid import UUID
import logging

from app.models.schemas import MessageResponse
from app.services.rag_service import get_rag_service, search_documents

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/rag/search")
async def search_rag(
    query: str = Query(..., description="检索查询文本"),
    top_k: int = Query(5, ge=1, le=20, description="返回数量"),
    artifact_id: Optional[str] = Query(None, description="限定文物ID"),
    artifact_name: Optional[str] = Query(None, description="限定文物名称"),
):
    """
    搜索相关文档

    - 根据查询文本在向量数据库中检索相似文档
    - 可指定文物ID或名称进行过滤
    """
    try:
        results = search_documents(
            query=query,
            top_k=top_k,
            artifact_id=artifact_id,
            artifact_name=artifact_name,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"RAG搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/artifacts/{artifact_id}/documents")
async def get_artifact_documents(artifact_id: str):
    """获取指定文物的所有文档"""
    try:
        rag_service = get_rag_service()
        docs = rag_service.get_by_artifact(artifact_id)
        return {"documents": docs, "count": len(docs)}
    except Exception as e:
        logger.error(f"获取文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/statistics")
async def get_rag_statistics():
    """获取RAG集合统计信息"""
    try:
        rag_service = get_rag_service()
        stats = rag_service.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rag/artifacts/{artifact_id}/documents")
async def delete_artifact_documents(artifact_id: str):
    """删除指定文物的所有文档"""
    try:
        rag_service = get_rag_service()
        count = rag_service.delete_by_artifact(artifact_id)
        return {"deleted": count, "message": f"成功删除 {count} 个文档"}
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/connect")
async def connect_rag():
    """手动连接RAG服务"""
    try:
        rag_service = get_rag_service()
        success = rag_service.connect(force=True)
        return {"success": success, "message": "连接成功" if success else "连接失败"}
    except Exception as e:
        logger.error(f"RAG连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/disconnect")
async def disconnect_rag():
    """断开RAG服务连接"""
    try:
        rag_service = get_rag_service()
        rag_service.disconnect()
        return {"success": True, "message": "已断开连接"}
    except Exception as e:
        logger.error(f"RAG断开连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
