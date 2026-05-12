from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from app.core.database import get_db
from app.models.artifact import Artifact, ArtifactStory, StoryType
from app.models.schemas import StoryGenerateRequest, StoryResponse, StoryContent
from app.services.gemma_service import get_gemma_service
from app.services.rag_service import get_rag_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def generate_story_content(artifact_id: UUID, artifact: Artifact, story_type: StoryType) -> dict:
    """
    使用 Gemma LLM + RAG 生成文物故事内容

    Args:
        artifact_id: 文物ID
        artifact: 文物对象
        story_type: 故事类型

    Returns:
        结构化的故事内容
    """
    try:
        # 1. 从 RAG 检索相关史料
        rag_service = get_rag_service()
        try:
            rag_service.connect()
            related_docs = rag_service.search(
                query=artifact.name,
                top_k=3,
                artifact_id=str(artifact_id),
            )
        except Exception as e:
            logger.warning(f"RAG 检索失败，使用空文档: {e}")
            related_docs = []

        # 2. 调用 Gemma 生成故事
        gemma_service = get_gemma_service()

        # 检查模型是否已加载
        if not gemma_service._loaded:
            logger.info("Gemma 模型未加载，尝试加载...")
            try:
                gemma_service.load_model()
            except Exception as e:
                logger.warning(f"Gemma 模型加载失败: {e}")
                # 返回占位内容
                return _generate_placeholder_story(artifact, str(e))

        # 3. 生成故事
        try:
            story_data = gemma_service.generate_artifact_story(
                artifact_name=artifact.name,
                dynasty=artifact.dynasty or "不详",
                category=artifact.category or "未分类",
                description=artifact.description or "",
                story_type=story_type.value,
                related_docs=related_docs,
            )
            return story_data
        except Exception as e:
            logger.error(f"Gemma 故事生成失败: {e}")
            return _generate_placeholder_story(artifact, str(e))

    except Exception as e:
        logger.error(f"故事生成过程异常: {e}")
        return _generate_placeholder_story(artifact, str(e))


def _generate_placeholder_story(artifact: Artifact, error: str = "") -> dict:
    """生成占位故事内容"""
    return {
        "origin": f"{artifact.name}的出土背景信息正在整理中...",
        "craftsmanship": f"{artifact.name}的制作工艺信息正在整理中...",
        "historical_context": f"{artifact.name}所在时期的历史背景信息正在整理中...",
        "cultural_significance": f"{artifact.name}的文化价值和意义正在整理中...",
        "related_events": ["历史事件信息整理中"],
        "similar_artifacts": ["相似文物信息整理中"],
        "note": f"注: {error}" if error else "注: 使用占位内容",
    }


async def run_story_generation(story_id: UUID, artifact_id: UUID, story_type: StoryType):
    """后台任务：生成故事"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # 获取故事记录
        query = select(ArtifactStory).where(ArtifactStory.id == story_id)
        result = await db.execute(query)
        story = result.scalar_one_or_none()

        if not story:
            logger.error(f"故事记录不存在: {story_id}")
            return

        # 获取文物信息
        artifact_query = select(Artifact).where(Artifact.id == artifact_id)
        artifact_result = await db.execute(artifact_query)
        artifact = artifact_result.scalar_one_or_none()

        if not artifact:
            logger.error(f"文物不存在: {artifact_id}")
            story.content = {"error": "文物不存在"}
            await db.commit()
            return

        try:
            # 生成故事内容
            content = await generate_story_content(artifact_id, artifact, story_type)
            story.content = content
            await db.commit()
            logger.info(f"故事生成成功: {story_id}")

        except Exception as e:
            logger.error(f"故事生成失败: {e}")
            story.content = {"error": str(e)}
            await db.commit()


@router.post("/stories/generate", response_model=StoryResponse, status_code=202)
async def generate_story(
    request: StoryGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    生成文物故事

    - 使用 RAG 检索相关史料
    - 使用 Gemma LLM 生成结构化故事
    - 故事异步生成，前端可通过轮询获取结果
    """
    # 检查文物是否存在
    query = select(Artifact).where(Artifact.id == request.artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="文物不存在")

    # 创建故事记录
    story = ArtifactStory(
        artifact_id=request.artifact_id,
        story_type=request.story_type.value,
        content={"status": "generating"},  # 标记为生成中
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)

    # 启动后台生成
    background_tasks.add_task(
        run_story_generation,
        story.id,
        request.artifact_id,
        request.story_type,
    )

    return StoryResponse(
        id=story.id,
        artifact_id=story.artifact_id,
        story_type=story.story_type,
        content=StoryContent(
            origin="正在生成中...",
            craftsmanship="正在生成中...",
            historical_context="正在生成中...",
            cultural_significance="正在生成中...",
            related_events=[],
            similar_artifacts=[],
        ),
        created_at=story.created_at,
    )


@router.get("/artifacts/{artifact_id}/story", response_model=StoryResponse)
async def get_artifact_story(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取文物的最新故事"""
    query = select(ArtifactStory).where(
        ArtifactStory.artifact_id == artifact_id
    ).order_by(ArtifactStory.created_at.desc()).limit(1)

    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="该文物没有生成故事")

    # 检查内容是否为错误
    if isinstance(story.content, dict) and "error" in story.content:
        raise HTTPException(
            status_code=500,
            detail=f"故事生成失败: {story.content['error']}"
        )

    # 检查内容是否还在生成中
    if isinstance(story.content, dict) and story.content.get("status") == "generating":
        raise HTTPException(status_code=202, detail="故事正在生成中")

    content = story.content if isinstance(story.content, dict) else {}
    return StoryResponse(
        id=story.id,
        artifact_id=story.artifact_id,
        story_type=story.story_type,
        content=StoryContent(**content) if content else StoryContent(),
        audio_url=story.audio_url,
        audio_script=story.audio_script,
        created_at=story.created_at,
    )


@router.get("/artifacts/{artifact_id}/stories", response_model=list[StoryResponse])
async def list_artifact_stories(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取文物的所有故事"""
    query = select(ArtifactStory).where(
        ArtifactStory.artifact_id == artifact_id
    ).order_by(ArtifactStory.created_at.desc())

    result = await db.execute(query)
    stories = result.scalars().all()

    return [
        StoryResponse(
            id=s.id,
            artifact_id=s.artifact_id,
            story_type=s.story_type,
            content=StoryContent(**(s.content if isinstance(s.content, dict) else {})),
            audio_url=s.audio_url,
            audio_script=s.audio_script,
            created_at=s.created_at,
        )
        for s in stories
    ]


@router.post("/stories/model/load")
async def load_story_model():
    """预加载 Gemma 模型"""
    from app.services.gemma_service import load_gemma_model

    success = load_gemma_model()
    return {"success": success, "message": "模型加载成功" if success else "模型加载失败"}


@router.post("/stories/model/unload")
async def unload_story_model():
    """卸载 Gemma 模型"""
    from app.services.gemma_service import get_gemma_service

    service = get_gemma_service()
    service.unload()
    return {"success": True, "message": "模型已卸载"}
