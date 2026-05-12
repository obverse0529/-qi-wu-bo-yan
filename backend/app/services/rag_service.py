"""
RAG (Retrieval-Augmented Generation) 服务
基于 Milvus 向量数据库的文物史料检索
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import json
import os

import torch
import numpy as np
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

from app.core.config import settings

logger = logging.getLogger(__name__)

# 史料来源类型常量
SOURCE_TYPE_UNKNOWN = "unknown"
SOURCE_TYPE_RESEARCH_PAPER = "research_paper"
SOURCE_TYPE_EXCAVATION_REPORT = "excavation_report"
SOURCE_TYPE_MUSEUM_DESCRIPTION = "museum_description"
SOURCE_TYPE_HISTORICAL_DOCUMENT = "historical_document"


class RAGService:
    """RAG 检索服务"""

    _instance: Optional["RAGService"] = None
    _connected: bool = False
    _collection: Optional[Collection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.host = settings.milvus_host
        self.port = settings.milvus_port
        self.collection_name = settings.milvus_collection
        self.embedding_model = settings.embedding_model
        self.embedding_dim = settings.embedding_dimension
        self._embedding_model = None
        self._initialized = False

    def _load_embedding_model(self):
        """加载文本嵌入模型"""
        if self._embedding_model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"加载嵌入模型: {self.embedding_model}")
            self._embedding_model = SentenceTransformer(self.embedding_model)
            logger.info("嵌入模型加载成功")
        except Exception as e:
            logger.error(f"嵌入模型加载失败: {e}")
            raise

    def connect(self, force: bool = False) -> bool:
        """
        连接 Milvus

        Args:
            force: 是否强制重连

        Returns:
            是否连接成功
        """
        if self._connected and not force:
            return True

        try:
            logger.info(f"连接 Milvus: {self.host}:{self.port}")

            # 连接
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )

            # 检查 collection 是否存在
            if utility.has_collection(self.collection_name):
                self._collection = Collection(self.collection_name)
                logger.info(f"已连接到 Collection: {self.collection_name}")
            else:
                logger.warning(f"Collection {self.collection_name} 不存在，将自动创建")
                self._create_collection()

            self._connected = True
            return True

        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            self._connected = False
            return False

    def _create_collection(self):
        """创建 Collection 和索引"""
        try:
            # 定义 schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="artifact_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="artifact_name", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="page", dtype=DataType.INT32),
                FieldSchema(name="year", dtype=DataType.INT32),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.embedding_dim,
                ),
            ]

            schema = CollectionSchema(
                fields=fields,
                description="文物史料向量库",
            )

            # 创建 collection
            self._collection = Collection(
                name=self.collection_name,
                schema=schema,
            )
            logger.info(f"Collection {self.collection_name} 创建成功")

            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 128},
            }

            self._collection.create_index(
                field_name="vector",
                index_params=index_params,
            )
            logger.info("向量索引创建成功")

        except Exception as e:
            logger.error(f"创建 Collection 失败: {e}")
            raise

    def disconnect(self):
        """断开 Milvus 连接"""
        if self._connected:
            connections.disconnect("default")
            self._connected = False
            self._collection = None
            logger.info("已断开 Milvus 连接")

    def _get_embedding(self, texts: List[str]) -> np.ndarray:
        """获取文本嵌入"""
        self._load_embedding_model()

        embeddings = self._embedding_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings

    def add_document(
        self,
        artifact_id: str,
        artifact_name: str,
        content: str,
        source: str,
        source_type: str = SOURCE_TYPE_UNKNOWN,
        page: int = 0,
        year: Optional[int] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """
        添加文档到向量库

        Args:
            artifact_id: 文物ID
            artifact_name: 文物名称
            content: 文档内容
            source: 来源
            source_type: 来源类型 (research_paper, excavation_report, museum_description 等)
            page: 页码
            year: 发布年份
            doc_id: 文档ID (不提供则自动生成)

        Returns:
            文档ID
        """
        if not self._connected:
            if not self.connect():
                raise RuntimeError("Milvus 连接失败")

        if doc_id is None:
            import uuid
            doc_id = str(uuid.uuid4())

        # 获取嵌入
        embedding = self._get_embedding([content])[0]

        # 插入数据
        data = [
            {
                "id": doc_id,
                "artifact_id": artifact_id,
                "artifact_name": artifact_name,
                "content": content,
                "source": source,
                "source_type": source_type,
                "page": page,
                "year": year or 0,
                "vector": embedding.tolist(),
            }
        ]

        self._collection.insert(data)
        self._collection.flush()

        logger.info(f"文档添加成功: {doc_id}")
        return doc_id

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        批量添加文档

        Args:
            documents: 文档列表，每项包含:
                - artifact_id: str
                - artifact_name: str
                - content: str
                - source: str
                - source_type: str (可选)
                - page: int (可选)
                - year: int (可选)

        Returns:
            文档ID列表
        """
        if not self._connected:
            if not self.connect():
                raise RuntimeError("Milvus 连接失败")

        self._load_embedding_model()

        # 批量获取嵌入
        contents = [doc["content"] for doc in documents]
        embeddings = self._get_embedding(contents)

        # 构建数据
        import uuid

        data = []
        doc_ids = []
        for i, doc in enumerate(documents):
            doc_id = doc.get("id") or str(uuid.uuid4())
            doc_ids.append(doc_id)

            data.append(
                {
                    "id": doc_id,
                    "artifact_id": doc["artifact_id"],
                    "artifact_name": doc["artifact_name"],
                    "content": doc["content"],
                    "source": doc["source"],
                    "source_type": doc.get("source_type", "unknown"),
                    "page": doc.get("page", 0),
                    "year": doc.get("year", 0),
                    "vector": embeddings[i].tolist(),
                }
            )

        self._collection.insert(data)
        self._collection.flush()

        logger.info(f"批量添加 {len(documents)} 个文档成功")
        return doc_ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        artifact_id: Optional[str] = None,
        artifact_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回数量
            artifact_id: 可选，限定文物ID
            artifact_name: 可选，限定文物名称

        Returns:
            相关文档列表
        """
        if not self._connected:
            if not self.connect():
                return []

        # 获取查询嵌入
        query_embedding = self._get_embedding([query])[0]

        # 构建搜索表达式
        filter_expr = None
        if artifact_id:
            filter_expr = f'arr_contains(artifact_id, "{artifact_id}")'
        elif artifact_name:
            filter_expr = f'artifact_name like "%{artifact_name}%"'

        # 搜索
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        results = self._collection.search(
            data=[query_embedding.tolist()],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["id", "artifact_id", "artifact_name", "content", "source", "source_type"],
        )

        # 整理结果
        docs = []
        for hits in results:
            for hit in hits:
                docs.append(
                    {
                        "id": hit.id,
                        "artifact_id": hit.entity.get("artifact_id"),
                        "artifact_name": hit.entity.get("artifact_name"),
                        "content": hit.entity.get("content"),
                        "source": hit.entity.get("source"),
                        "source_type": hit.entity.get("source_type"),
                        "score": hit.distance,
                    }
                )

        return docs

    def get_by_artifact(self, artifact_id: str) -> List[Dict[str, Any]]:
        """
        获取指定文物的所有文档

        Args:
            artifact_id: 文物ID

        Returns:
            文档列表
        """
        if not self._connected:
            if not self.connect():
                return []

        results = self._collection.query(
            expr=f'artifact_id == "{artifact_id}"',
            output_fields=["id", "artifact_id", "artifact_name", "content", "source", "source_type"],
        )

        return [
            {
                "id": r["id"],
                "artifact_id": r["artifact_id"],
                "artifact_name": r["artifact_name"],
                "content": r["content"],
                "source": r["source"],
                "source_type": r["source_type"],
            }
            for r in results
        ]

    def delete_by_artifact(self, artifact_id: str) -> int:
        """
        删除指定文物的所有文档

        Args:
            artifact_id: 文物ID

        Returns:
            删除的文档数量
        """
        if not self._connected:
            if not self.connect():
                return 0

        # 先查询数量
        results = self._collection.query(
            expr=f'artifact_id == "{artifact_id}"',
            output_fields=["id"],
        )
        count = len(results)

        if count > 0:
            # 删除
            ids = [r["id"] for r in results]
            delete_expr = f'id in {ids}'
            self._collection.delete(delete_expr)
            self._collection.flush()

        logger.info(f"删除 {count} 个文档")
        return count

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        if not self._connected:
            if not self.connect():
                return {"status": "disconnected"}

        stats = {
            "name": self.collection_name,
            "count": self._collection.num_entities,
            "connected": self._connected,
        }

        return stats


# 全局单例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """获取 RAG 服务单例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def init_rag_service() -> bool:
    """初始化 RAG 服务"""
    service = get_rag_service()
    return service.connect()


def search_documents(
    query: str,
    top_k: int = 5,
    artifact_id: Optional[str] = None,
    artifact_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """搜索相关文档"""
    service = get_rag_service()
    return service.search(query, top_k, artifact_id, artifact_name)
