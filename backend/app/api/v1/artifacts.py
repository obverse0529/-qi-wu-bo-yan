from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.models.artifact import Artifact
from app.models.schemas import (
    ArtifactCreate, ArtifactUpdate, ArtifactResponse, ArtifactListResponse,
    PaginationParams, MessageResponse
)

router = APIRouter()


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    category: Optional[str] = Query(None, description="按类别筛选"),
    dynasty: Optional[str] = Query(None, description="按朝代筛选"),
    search: Optional[str] = Query(None, description="搜索名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取文物列表，支持分页和筛选"""
    query = select(Artifact)

    # Apply filters
    if category:
        query = query.where(Artifact.category == category)
    if dynasty:
        query = query.where(Artifact.dynasty == dynasty)
    if search:
        query = query.where(Artifact.name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(Artifact.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    artifacts = result.scalars().all()

    return ArtifactListResponse(
        items=[ArtifactResponse.model_validate(a) for a in artifacts],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.post("", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    artifact_data: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新文物"""
    artifact = Artifact(**artifact_data.model_dump())
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取单个文物详情"""
    query = select(Artifact).where(Artifact.id == artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="文物不存在")

    return ArtifactResponse.model_validate(artifact)


@router.put("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: UUID,
    artifact_data: ArtifactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文物信息"""
    query = select(Artifact).where(Artifact.id == artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="文物不存在")

    update_data = artifact_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(artifact, key, value)

    await db.commit()
    await db.refresh(artifact)
    return ArtifactResponse.model_validate(artifact)


@router.delete("/{artifact_id}", response_model=MessageResponse)
async def delete_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除文物"""
    query = select(Artifact).where(Artifact.id == artifact_id)
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="文物不存在")

    await db.delete(artifact)
    await db.commit()

    return MessageResponse(message="文物删除成功")


@router.get("/categories/list")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取所有文物类别"""
    query = select(Artifact.category, func.count(Artifact.id)).group_by(Artifact.category)
    result = await db.execute(query)
    categories = [{"name": row[0], "count": row[1]} for row in result.all() if row[0]]
    return categories


@router.get("/dynasties/list")
async def list_dynasties(db: AsyncSession = Depends(get_db)):
    """获取所有朝代"""
    query = select(Artifact.dynasty, func.count(Artifact.id)).group_by(Artifact.dynasty)
    result = await db.execute(query)
    dynasties = [{"name": row[0], "count": row[1]} for row in result.all() if row[0]]
    return dynasties
