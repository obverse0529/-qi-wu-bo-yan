from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime
import logging
import os

from app.core.config import settings
from app.core.database import get_db
from app.models.artifact import Artifact, ArtifactImage, ArtifactModel, ReconstructionTask, ReconstructionStatus
from app.models.schemas import ReconstructionSubmit, ReconstructionResponse, MessageResponse
from app.services.hunyuan3d_service import get_hunyuan3d_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def run_reconstruction(task_id: UUID, artifact_id: UUID):
    """后台任务：执行3D重建"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # 获取任务
        query = select(ReconstructionTask).where(ReconstructionTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            logger.error(f"重建任务不存在: {task_id}")
            return

        try:
            # 更新状态为运行中
            task.status = ReconstructionStatus.RUNNING.value
            task.started_at = datetime.utcnow()
            await db.commit()

            # 获取文物图像
            img_query = select(ArtifactImage).where(ArtifactImage.artifact_id == artifact_id)
            img_result = await db.execute(img_query)
            images = img_result.scalars().all()

            if len(images) < 4:
                raise ValueError(f"需要至少4张图像，当前只有{len(images)}张")

            # 获取图像路径
            image_paths = [img.file_path for img in images if img.file_path and os.path.exists(img.file_path)]

            if len(image_paths) < 4:
                raise ValueError(f"有效图像不足，需要至少4张，当前只有{len(image_paths)}张")

            logger.info(f"开始重建，图像数量: {len(image_paths)}")

            # 获取混元3D服务
            hunyuan_service = get_hunyuan3d_service()

            # 检查模型是否已加载
            if not hunyuan_service._loaded:
                logger.info("加载混元3D模型...")
                hunyuan_service._load_model()

            # 更新进度
            task.progress = 10
            await db.commit()

            # 执行重建
            # 生成输出路径
            output_dir = settings.processed_models_dir / str(artifact_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{artifact_id}.glb"

            # 更新进度
            task.progress = 30
            await db.commit()

            # 执行3D重建
            result = hunyuan_service.reconstruct(
                image_paths=image_paths,
                output_path=output_path,
                resolution=256,
                texture_size=1024,
            )

            # 更新进度
            task.progress = 90
            await db.commit()

            # 创建模型记录
            model = ArtifactModel(
                artifact_id=artifact_id,
                model_url=result.get("model_url"),
                file_path=result.get("model_path"),
                polygon_count=result.get("polygon_count", 50000),
                has_texture=result.get("has_texture", True),
                file_size=result.get("file_size", 0),
                status="completed",
            )
            db.add(model)
            await db.flush()

            # 更新任务状态
            task.status = ReconstructionStatus.COMPLETED.value
            task.progress = 100
            task.model_id = model.id
            task.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(f"3D重建任务完成: {task_id}")

        except Exception as e:
            logger.error(f"3D重建失败: {e}")
            task.status = ReconstructionStatus.FAILED.value
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            await db.commit()


@router.post("/reconstruct", response_model=ReconstructionResponse, status_code=202)
async def submit_reconstruction(
    request: ReconstructionSubmit,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    提交3D重建任务

    - 需要文物至少上传4张多视图图像
    - 任务异步执行，前端可通过轮询查询状态
    """
    # 检查文物是否存在
    query = select(Artifact).where(Artifact.id == request.artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="文物不存在")

    # 检查是否有正在运行的任务
    running_query = select(ReconstructionTask).where(
        ReconstructionTask.artifact_id == request.artifact_id,
        ReconstructionTask.status.in_([
            ReconstructionStatus.PENDING.value,
            ReconstructionStatus.RUNNING.value,
        ]),
    )
    running_result = await db.execute(running_query)

    if running_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该文物已有正在进行的重建任务")

    # 检查图像数量
    img_count_query = select(func.count()).select_from(ArtifactImage).where(ArtifactImage.artifact_id == request.artifact_id)
    img_count_result = await db.execute(img_count_query)
    image_count = img_count_result.scalar() or 0

    if image_count < 4:
        raise HTTPException(
            status_code=400,
            detail=f"图像数量不足，需要至少4张，当前只有{image_count}张"
        )

    # 创建重建任务
    task = ReconstructionTask(
        artifact_id=request.artifact_id,
        status=ReconstructionStatus.PENDING.value,
        progress=0,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动后台重建
    background_tasks.add_task(run_reconstruction, task.id, request.artifact_id)

    return ReconstructionResponse.model_validate(task)


@router.get("/reconstruct/{task_id}", response_model=ReconstructionResponse)
async def get_reconstruction_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取重建任务状态"""
    query = select(ReconstructionTask).where(ReconstructionTask.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return ReconstructionResponse.model_validate(task)


@router.get("/artifacts/{artifact_id}/reconstruction", response_model=ReconstructionResponse)
async def get_artifact_reconstruction(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取文物的最新重建任务"""
    query = select(ReconstructionTask).where(
        ReconstructionTask.artifact_id == artifact_id
    ).order_by(ReconstructionTask.created_at.desc()).limit(1)

    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="该文物没有重建任务")

    return ReconstructionResponse.model_validate(task)


@router.get("/artifacts/{artifact_id}/model", response_model=dict)
async def get_artifact_model(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取文物的3D模型"""
    query = select(ArtifactModel).where(
        ArtifactModel.artifact_id == artifact_id,
        ArtifactModel.status == "completed",
    ).order_by(ArtifactModel.created_at.desc()).limit(1)

    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="该文物没有已完成的3D模型")

    return {
        "id": str(model.id),
        "artifact_id": str(model.artifact_id),
        "model_url": model.model_url,
        "file_path": model.file_path,
        "polygon_count": model.polygon_count,
        "has_texture": model.has_texture,
        "file_size": model.file_size,
    }


@router.post("/reconstruct/model/load")
async def load_reconstruct_model():
    """预加载混元3D模型"""
    from app.services.hunyuan3d_service import load_hunyuan3d_model

    success = load_hunyuan3d_model()
    return {"success": success, "message": "模型加载成功" if success else "模型加载失败"}


@router.post("/reconstruct/model/unload")
async def unload_reconstruct_model():
    """卸载混元3D模型"""
    from app.services.hunyuan3d_service import unload_hunyuan3d_model

    unload_hunyuan3d_model()
    return {"success": True, "message": "模型已卸载"}
