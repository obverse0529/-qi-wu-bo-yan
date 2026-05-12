"""
知识图谱服务
基于 Neo4j 的文物知识图谱构建和查询
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from uuid import UUID
import json

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.core.config import settings

logger = logging.getLogger(__name__)

# 节点标签常量
NODE_ARTIFACT = "Artifact"
NODE_DYNASTY = "Dynasty"
NODE_CATEGORY = "Category"
NODE_SITE = "Site"
NODE_TECHNIQUE = "Technique"
NODE_MATERIAL = "Material"
NODE_PERSON = "Person"
NODE_EVENT = "Event"
NODE_MUSEUM = "Museum"

# 关系类型常量
REL_BELONGS_TO_DYNASTY = "BELONGS_TO_DYNASTY"
REL_CATEGORY_IS = "CATEGORY_IS"
REL_EXCAVATED_FROM = "EXCAVATED_FROM"
REL_MADE_USING = "MADE_USING"
REL_MADE_OF = "MADE_OF"
REL_MADE_BY = "MADE_BY"
REL_RELATED_TO = "RELATED_TO"
REL_SIMILAR_TO = "SIMILAR_TO"
REL_SAME_DYNASTY = "SAME_DYNASTY"
REL_SAME_CATEGORY = "SAME_CATEGORY"
REL_COLLECTED_BY = "COLLECTED_BY"


class KnowledgeGraphService:
    """Neo4j 知识图谱服务"""

    _instance: Optional["KnowledgeGraphService"] = None
    _driver = None
    _connected: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password

    def connect(self, force: bool = False) -> bool:
        """
        连接 Neo4j

        Args:
            force: 是否强制重连

        Returns:
            是否连接成功
        """
        if self._connected and self._driver is not None and not force:
            return True

        try:
            logger.info(f"连接 Neo4j: {self.uri}")

            # 关闭旧连接
            if self._driver is not None:
                self._driver.close()

            # 创建新连接
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
            )

            # 验证连接
            self._driver.verify_connectivity()
            self._connected = True

            logger.info("Neo4j 连接成功")
            return True

        except AuthError as e:
            logger.error(f"Neo4j 认证失败: {e}")
            self._connected = False
            return False
        except ServiceUnavailable as e:
            logger.error(f"Neo4j 服务不可用: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Neo4j 连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """断开 Neo4j 连接"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("已断开 Neo4j 连接")

    def _run_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行 Cypher 查询"""
        if not self._connected or self._driver is None:
            if not self.connect():
                raise RuntimeError("Neo4j 连接失败")

        with self._driver.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def create_artifact_node(
        self,
        artifact_id: str,
        name: str,
        dynasty: Optional[str] = None,
        category: Optional[str] = None,
        **properties,
    ) -> bool:
        """
        创建文物节点

        Args:
            artifact_id: 文物ID (UUID)
            name: 文物名称
            dynasty: 朝代
            category: 分类
            **properties: 其他属性

        Returns:
            是否创建成功
        """
        query = """
        MERGE (a:Artifact {artifact_id: $artifact_id})
        SET a.name = $name,
            a.dynasty = $dynasty,
            a.category = $category,
            a.updated_at = timestamp()
        WITH a
        FOREACH (k IN keys($properties) |
            SET a[k] = $properties[k]
        )
        RETURN a.artifact_id as id
        """

        params = {
            "artifact_id": artifact_id,
            "name": name,
            "dynasty": dynasty or "",
            "category": category or "",
            "properties": properties,
        }

        try:
            result = self._run_query(query, params)
            return len(result) > 0
        except Exception as e:
            logger.error(f"创建文物节点失败: {e}")
            return False

    def create_relationship(
        self,
        artifact_id: str,
        target_id: str,
        target_label: str,
        relationship_type: str,
        properties: Optional[Dict] = None,
    ) -> bool:
        """
        创建文物与目标节点的关系

        Args:
            artifact_id: 文物ID
            target_id: 目标节点ID
            target_label: 目标节点标签 (Dynasty, Category, Site, Technique 等)
            relationship_type: 关系类型
            properties: 关系属性

        Returns:
            是否创建成功
        """
        query = f"""
        MATCH (a:Artifact {{artifact_id: $artifact_id}})
        MERGE (t:{target_label} {{id: $target_id}})
        MERGE (a)-[r:{relationship_type}]->(t)
        SET r += $properties
        RETURN a.artifact_id as id
        """

        params = {
            "artifact_id": artifact_id,
            "target_id": target_id,
            "properties": properties or {},
        }

        try:
            result = self._run_query(query, params)
            return len(result) > 0
        except Exception as e:
            logger.error(f"创建关系失败: {e}")
            return False

    def query_artifact_graph(
        self,
        artifact_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        查询文物的完整图谱信息

        Args:
            artifact_id: 文物ID
            depth: 查询深度

        Returns:
            包含节点和边的图谱数据
        """
        query = f"""
        MATCH (a:Artifact {{artifact_id: $artifact_id}})
        OPTIONAL MATCH path = (a)-[r]-(connected)
        WITH a, r, connected, relationships(path) as rels
        LIMIT 100
        WITH collect(DISTINCT {{node: a, rel: null}}) +
             collect(DISTINCT {{node: connected, rel: r}}) as all_elements
        UNWIND all_elements as element
        WITH element.node as node, element.rel as rel
        WHERE node IS NOT NULL
        WITH collect(DISTINCT node) as nodes,
             collect(DISTINCT rel) as relationships
        RETURN nodes, relationships
        """

        params = {"artifact_id": artifact_id}

        try:
            result = self._run_query(query, params)
            if not result:
                return {"nodes": [], "edges": []}

            record = result[0]
            nodes = []
            edges = []

            # 处理节点
            for node_data in record.get("nodes", []):
                if node_data is None:
                    continue
                node_props = dict(node_data)
                labels = node_data.keys() if hasattr(node_data, 'keys') else []
                nodes.append(
                    {
                        "id": node_props.get("artifact_id") or node_props.get("id", ""),
                        "label": labels[0] if labels else "Unknown",
                        "properties": {k: v for k, v in node_props.items() if not k.startswith("_")},
                    }
                )

            # 处理关系
            for rel in record.get("relationships", []):
                if rel is None:
                    continue
                edges.append(
                    {
                        "source": rel.start_node.element_id if hasattr(rel.start_node, 'element_id') else str(rel.start_node),
                        "target": rel.end_node.element_id if hasattr(rel.end_node, 'element_id') else str(rel.end_node),
                        "type": rel.type,
                        "properties": dict(rel),
                    }
                )

            return {"nodes": nodes, "edges": edges}

        except Exception as e:
            logger.error(f"查询图谱失败: {e}")
            return {"nodes": [], "edges": []}

    def search_related_artifacts(
        self,
        artifact_id: str,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索相关文物

        Args:
            artifact_id: 文物ID
            relationship_types: 关系类型列表 (如 ["RELATED_TO", "SIMILAR_TO"])
            limit: 返回数量

        Returns:
            相关文物列表
        """
        if relationship_types is None:
            relationship_types = [REL_RELATED_TO, REL_SIMILAR_TO, REL_SAME_DYNASTY, REL_SAME_CATEGORY]

        rel_types_str = "|".join(relationship_types)

        query = f"""
        MATCH (a:Artifact {{artifact_id: $artifact_id}})-[r:{rel_types_str}]-(related:Artifact)
        RETURN related.artifact_id as artifact_id,
               related.name as name,
               related.dynasty as dynasty,
               related.category as category,
               type(r) as relationship
        LIMIT $limit
        """

        params = {"artifact_id": artifact_id, "limit": limit}

        try:
            result = self._run_query(query, params)
            return [
                {
                    "artifact_id": r["artifact_id"],
                    "name": r["name"],
                    "dynasty": r.get("dynasty"),
                    "category": r.get("category"),
                    "relationship": r["relationship"],
                }
                for r in result
            ]
        except Exception as e:
            logger.error(f"搜索相关文物失败: {e}")
            return []

    def search_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        通过关键词搜索节点

        Args:
            keyword: 关键词
            limit: 返回数量

        Returns:
            匹配的节点列表
        """
        query = """
        MATCH (n)
        WHERE n.name CONTAINS $keyword OR n.artifact_id CONTAINS $keyword
        WITH labels(n)[0] as label, n, size((n)--()) as degree
        RETURN n.artifact_id as id,
               n.name as name,
               label,
               n.dynasty as dynasty,
               n.category as category,
               degree
        LIMIT $limit
        """

        params = {"keyword": keyword, "limit": limit}

        try:
            result = self._run_query(query, params)
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "label": r["label"],
                    "dynasty": r.get("dynasty"),
                    "category": r.get("category"),
                    "degree": r.get("degree", 0),
                }
                for r in result
            ]
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []

    def build_from_artifact_data(
        self,
        artifact_id: str,
        name: str,
        dynasty: str,
        category: str,
        site: Optional[str] = None,
        techniques: Optional[List[str]] = None,
        materials: Optional[List[str]] = None,
    ) -> bool:
        """
        从文物数据构建图谱

        Args:
            artifact_id: 文物ID
            name: 文物名称
            dynasty: 朝代
            category: 分类
            site: 出土地点
            techniques: 工艺列表
            materials: 材质列表

        Returns:
            是否构建成功
        """
        try:
            # 创建文物节点
            self.create_artifact_node(
                artifact_id=artifact_id,
                name=name,
                dynasty=dynasty,
                category=category,
            )

            # 创建朝代关系
            if dynasty:
                self.create_relationship(
                    artifact_id=artifact_id,
                    target_id=dynasty,
                    target_label=NODE_DYNASTY,
                    relationship_type=REL_BELONGS_TO_DYNASTY,
                )

            # 创建分类关系
            if category:
                self.create_relationship(
                    artifact_id=artifact_id,
                    target_id=category,
                    target_label=NODE_CATEGORY,
                    relationship_type=REL_CATEGORY_IS,
                )

            # 创建出土地点关系
            if site:
                self.create_relationship(
                    artifact_id=artifact_id,
                    target_id=site,
                    target_label=NODE_SITE,
                    relationship_type=REL_EXCAVATED_FROM,
                )

            # 创建工艺关系
            if techniques:
                for technique in techniques:
                    self.create_relationship(
                        artifact_id=artifact_id,
                        target_id=technique,
                        target_label=NODE_TECHNIQUE,
                        relationship_type=REL_MADE_USING,
                    )

            # 创建材质关系
            if materials:
                for material in materials:
                    self.create_relationship(
                        artifact_id=artifact_id,
                        target_id=material,
                        target_label=NODE_MATERIAL,
                        relationship_type=REL_MADE_OF,
                    )

            # 创建相似文物关系 (同朝代)
            if dynasty:
                query = f"""
                MATCH (a:Artifact {{artifact_id: $artifact_id, dynasty: $dynasty}})
                MATCH (a)-[r:{REL_SAME_DYNASTY}]-(related:Artifact)
                RETURN count(related) as count
                """
                try:
                    self._run_query(query, {"artifact_id": artifact_id, "dynasty": dynasty})
                except Exception:
                    pass

            logger.info(f"文物图谱构建成功: {artifact_id}")
            return True

        except Exception as e:
            logger.error(f"构建文物图谱失败: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        query = """
        MATCH (n)
        WITH labels(n)[0] as label, count(*) as count
        RETURN label, count
        ORDER BY count DESC
        """

        try:
            result = self._run_query(query)
            return {"node_counts": {r["label"]: r["count"] for r in result}}
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"node_counts": {}}

    def delete_artifact(self, artifact_id: str) -> bool:
        """删除文物节点及其所有关系"""
        query = """
        MATCH (a:Artifact {artifact_id: $artifact_id})
        DETACH DELETE a
        RETURN count(*) as deleted
        """

        try:
            result = self._run_query(query, {"artifact_id": artifact_id})
            deleted = result[0]["deleted"] if result else 0
            logger.info(f"删除文物节点: {artifact_id}, 数量: {deleted}")
            return deleted > 0
        except Exception as e:
            logger.error(f"删除文物节点失败: {e}")
            return False


# 全局单例
_kg_service: Optional[KnowledgeGraphService] = None


def get_kg_service() -> KnowledgeGraphService:
    """获取知识图谱服务单例"""
    global _kg_service
    if _kg_service is None:
        _kg_service = KnowledgeGraphService()
    return _kg_service


def init_kg_service() -> bool:
    """初始化知识图谱服务"""
    service = get_kg_service()
    return service.connect()


def disconnect_kg_service():
    """断开知识图谱服务"""
    global _kg_service
    if _kg_service is not None:
        _kg_service.disconnect()
        _kg_service = None
