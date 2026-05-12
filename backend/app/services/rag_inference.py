"""
RAG 增强推理服务
用于长期方案：学生模型(qwen2.5:3b) + RAG 实时检索文物史料

在推理时，模型生成前先从 Milvus 检索相关文物史料，
拼接到 prompt 中，增强生成质量、减少幻觉
"""

import logging
from typing import List, Dict, Any, Optional

from app.services.rag_service import get_rag_service, search_documents
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGEnhancedInference:
    """
    RAG 增强的文物故事生成推理

    流程:
    1. 接收用户查询（如"介绍后母戊鼎"）
    2. RAG 检索相关文物史料
    3. 拼接检索结果到 prompt
    4. 调用学生模型生成
    """

    def __init__(self, model_service):
        """
        Args:
            model_service: 底层的模型服务（如 qwen2.5:3b 推理服务）
        """
        self.model_service = model_service
        self.rag_service = get_rag_service()
        self.top_k = settings.rag_top_k

    def generate_with_rag(
        self,
        artifact_name: str,
        dynasty: str,
        category: str,
        query: Optional[str] = None,
        **generation_kwargs,
    ) -> Dict[str, Any]:
        """
        RAG 增强的文物故事生成

        Args:
            artifact_name: 文物名称
            dynasty: 朝代
            category: 分类
            query: 可选的查询文本，不提供则用文物信息构造
            **generation_kwargs: 传递给模型的其他参数

        Returns:
            {
                "story": "生成的故事文本",
                "sources": [{"content": "...", "source": "...", "score": ...}],
                "rag_retrieved": True
            }
        """
        # 1. RAG 检索相关史料
        search_query = query or f"{artifact_name} {dynasty} {category}"
        retrieved_docs = search_documents(
            query=search_query,
            top_k=self.top_k,
            artifact_name=artifact_name,
        )

        # 2. 拼接上下文
        context_parts = []
        for doc in retrieved_docs:
            context_parts.append(
                f"【{doc.get('source', '未知来源')}】\n{doc.get('content', '')}"
            )

        context = "\n\n".join(context_parts) if context_parts else ""

        # 3. 构建增强 prompt
        if context:
            enhanced_prompt = self._build_enhanced_prompt(
                artifact_name, dynasty, category, context
            )
        else:
            enhanced_prompt = self._build_basic_prompt(
                artifact_name, dynasty, category
            )

        # 4. 调用模型生成
        story = self.model_service.generate(
            prompt=enhanced_prompt,
            **generation_kwargs,
        )

        return {
            "story": story,
            "sources": retrieved_docs,
            "rag_retrieved": len(retrieved_docs) > 0,
            "context_used": bool(context),
        }

    def _build_enhanced_prompt(
        self,
        artifact_name: str,
        dynasty: str,
        category: str,
        context: str,
    ) -> str:
        """构建带 RAG 上下文的 prompt"""
        return f"""你是一个专业的中国博物馆文物讲解员。请根据以下文物信息和参考史料，写一段详细的文物介绍。

文物信息：
- 名称：{artifact_name}
- 朝代：{dynasty}
- 分类：{category}

参考史料：
{context}

请结合参考史料，写一段生动、专业的文物介绍："""

    def _build_basic_prompt(
        self,
        artifact_name: str,
        dynasty: str,
        category: str,
    ) -> str:
        """构建基础 prompt（无 RAG 上下文）"""
        return f"""你是一个专业的中国博物馆文物讲解员。请根据以下文物信息，写一段详细的文物介绍。

文物信息：
- 名称：{artifact_name}
- 朝代：{dynasty}
- 分类：{category}

请写一段生动、专业的文物介绍："""

    def batch_generate_with_rag(
        self,
        artifacts: List[Dict[str, Any]],
        **generation_kwargs,
    ) -> List[Dict[str, Any]]:
        """
        批量 RAG 增强生成

        Args:
            artifacts: 文物列表，每项包含 artifact_name, dynasty, category

        Returns:
            生成结果列表
        """
        results = []
        for artifact in artifacts:
            result = self.generate_with_rag(
                artifact_name=artifact.get("artifact_name", artifact.get("name", "")),
                dynasty=artifact.get("dynasty", ""),
                category=artifact.get("category", ""),
                **generation_kwargs,
            )
            results.append({
                "artifact_id": artifact.get("artifact_id", ""),
                **result,
            })
        return results


def create_rag_enhanced_service(model_service) -> RAGEnhancedInference:
    """创建 RAG 增强推理服务"""
    return RAGEnhancedInference(model_service)
