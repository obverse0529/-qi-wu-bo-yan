from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime
import os
import uuid as uuid_lib
from PIL import Image
import io

from app.core.database import get_db
from app.core.config import settings
from app.models.artifact import Artifact, ArtifactImage
from app.models.schemas import ImageResponse, MessageResponse

router = APIRouter()

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "dataset", "raw", "artifacts")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{artifact_id}/images", response_model=ImageResponse)
async def upload_image(
    artifact_id: UUID,
    file: UploadFile = File(...),
    view_type: str = Query(None, description="视角类型: front, side_left, side_right, back, top, bottom"),
    db: AsyncSession = Depends(get_db),
):
    """上传文物图像"""
    # Check artifact exists
    query = select(Artifact).where(Artifact.id == artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="文物不存在")

    # Validate file type
    if file.content_type not in settings.allowed_image_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型，仅支持: {settings.allowed_image_types}")

    # Read and validate image
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents))
        width, height = img.size
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效的图像文件: {str(e)}")

    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{artifact_id}_{view_type or 'unknown'}_{uuid_lib.uuid4().hex[:8]}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, str(artifact_id))
    os.makedirs(file_path, exist_ok=True)
    full_path = os.path.join(file_path, filename)

    # Save file
    with open(full_path, "wb") as f:
        f.write(contents)

    # Create database record
    image_url = f"/uploads/artifacts/{artifact_id}/{filename}"
    image = ArtifactImage(
        artifact_id=artifact_id,
        view_type=view_type,
        image_url=image_url,
        file_path=full_path,
        width=width,
        height=height,
        file_size=len(contents),
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    return ImageResponse.model_validate(image)


@router.get("/{artifact_id}/images", response_model=list[ImageResponse])
async def list_images(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取文物的所有图像"""
    query = select(ArtifactImage).where(ArtifactImage.artifact_id == artifact_id).order_by(ArtifactImage.created_at)
    result = await db.execute(query)
    images = result.scalars().all()
    return [ImageResponse.model_validate(img) for img in images]


@router.delete("/{artifact_id}/images/{image_id}", response_model=MessageResponse)
async def delete_image(
    artifact_id: UUID,
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除文物图像"""
    query = select(ArtifactImage).where(
        ArtifactImage.id == image_id,
        ArtifactImage.artifact_id == artifact_id
    )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="图像不存在")

    # Delete file if exists
    if image.file_path and os.path.exists(image.file_path):
        os.remove(image.file_path)

    await db.delete(image)
    await db.commit()

    return MessageResponse(message="图像删除成功")
