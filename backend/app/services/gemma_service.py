"""
Gemma LLM 服务
基于 Google Gemma 3 (Ollama 本地推理)
"""

import json
import logging
import os
import re
from typing import Optional, List, Dict, Any

import requests

from app.core.config import settings

# 系统提示词模板
ARTIFACT_STORY_SYSTEM_PROMPT = """你是一位专业的文物讲解员，擅长讲述文物背后的历史故事。
请根据提供的信息，生成一段生动的文物介绍故事。
故事应包含以下方面：
1. 出土背景和发现过程 (origin)
2. 制作工艺详解 (craftsmanship)
3. 所在时期的历史背景 (historical_context)
4. 文化价值和意义 (cultural_significance)
5. 相关历史事件 (related_events) - 列出3-5个
6. 相似文物推荐 (similar_artifacts) - 列出3-5个

请以 JSON 格式返回，包含以下字段：
- origin: string
- craftsmanship: string
- historical_context: string
- cultural_significance: string
- related_events: string[]
- similar_artifacts: string[]

请用中文回答。"""

logger = logging.getLogger(__name__)


class GemmaService:
    """Gemma 3 Ollama 推理服务"""

    _instance: Optional["GemmaService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.model_name = settings.gemma_model_name
        self.base_url = settings.gemma_ollama_base_url
        self.max_length = settings.gemma_max_length
        self._available = None

    def check_health(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                self._available = self.model_name in model_names
                if not self._available:
                    logger.warning(f"模型 {self.model_name} 未在 Ollama 中找到，可用模型: {model_names}")
                return self._available
            return False
        except Exception as e:
            logger.error(f"Ollama 服务不可用: {e}")
            self._available = False
            return False

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        生成文本 (使用 Ollama API)

        Args:
            prompt: 用户输入
            max_new_tokens: 最大生成长度
            temperature: 温度参数
            top_p: top-p 采样
            system_prompt: 系统提示

        Returns:
            生成的文本
        """
        # 构建消息格式
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_new_tokens,
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            else:
                logger.error(f"Ollama API 错误: {response.status_code} - {response.text}")
                raise RuntimeError(f"生成失败: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error("Ollama 请求超时")
            raise RuntimeError("生成超时，请稍后重试")
        except Exception as e:
            logger.error(f"生成文本失败: {e}")
            raise

    def generate_artifact_story(
        self,
        artifact_name: str,
        dynasty: str,
        category: str,
        description: str,
        story_type: str = "standard",
        related_docs: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        生成文物故事

        Args:
            artifact_name: 文物名称
            dynasty: 朝代
            category: 分类
            description: 描述
            story_type: 故事类型 (brief/standard/detailed)
            related_docs: 相关史料 (RAG检索结果)

        Returns:
            结构化的故事 JSON
        """
        # 根据类型确定长度
        length_map = {
            "brief": "约100字，简短介绍",
            "standard": "约300字，详细介绍",
            "detailed": "约800字，全面深入",
        }
        length_hint = length_map.get(story_type, "约300字")

        # 构建用户提示
        context_parts = [
            f"文物名称：{artifact_name}",
            f"所属年代：{dynasty}",
            f"文物分类：{category}",
            f"文物描述：{description}" if description else "",
        ]

        if related_docs:
            context_parts.append("\n相关史料：")
            for i, doc in enumerate(related_docs[:3], 1):
                context_parts.append(f"[{i}] {doc.get('content', '')[:200]}...")

        context_parts.append(f"\n请生成一段{length_hint}的文物故事，按照上述 JSON 格式返回。")

        user_prompt = "\n".join(context_parts)

        try:
            # 生成
            response = self.generate(
                prompt=user_prompt,
                system_prompt=ARTIFACT_STORY_SYSTEM_PROMPT,
                max_new_tokens=2048,
                temperature=0.7,
            )

            # 提取 JSON
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                story_data = json.loads(json_match.group())
            else:
                raise ValueError("无法解析故事 JSON")

            return story_data

        except Exception as e:
            logger.error(f"生成文物故事失败: {e}")
            return {
                "origin": f"关于{artifact_name}的背景信息生成失败",
                "craftsmanship": "工艺信息生成失败",
                "historical_context": "历史背景信息生成失败",
                "cultural_significance": "文化意义信息生成失败",
                "related_events": [],
                "similar_artifacts": [],
                "error": str(e),
            }


# 全局单例
_gemma_service: Optional[GemmaService] = None


def get_gemma_service() -> GemmaService:
    """获取 Gemma 服务单例"""
    global _gemma_service
    if _gemma_service is None:
        _gemma_service = GemmaService()
    return _gemma_service


def check_gemma_health() -> bool:
    """检查 Gemma/Ollama 服务健康状态"""
    service = get_gemma_service()
    return service.check_health()
