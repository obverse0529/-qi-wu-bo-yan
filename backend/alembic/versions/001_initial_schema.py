"""Initial schema — all core tables

Revision ID: 001
Revises:
Create Date: 2026-05-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- artifacts ---
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dynasty", sa.String(100)),
        sa.Column("category", sa.String(100)),
        sa.Column("dimensions", postgresql.JSONB),
        sa.Column("description", sa.Text),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_artifacts_name", "artifacts", ["name"])
    op.create_index("ix_artifacts_dynasty", "artifacts", ["dynasty"])
    op.create_index("ix_artifacts_category", "artifacts", ["category"])

    # --- artifact_images ---
    op.create_table(
        "artifact_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("view_type", sa.String(50)),
        sa.Column("image_url", sa.String(500)),
        sa.Column("thumbnail_url", sa.String(500)),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("file_size", sa.BigInteger),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- artifact_models ---
    op.create_table(
        "artifact_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_url", sa.String(500)),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("polygon_count", sa.Integer),
        sa.Column("has_texture", sa.Boolean, default=True),
        sa.Column("file_size", sa.BigInteger),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- reconstruction_tasks ---
    op.create_table(
        "reconstruction_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("progress", sa.Integer, default=0),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifact_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- artifact_stories ---
    op.create_table(
        "artifact_stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("story_type", sa.String(50), default="standard"),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("audio_url", sa.String(500), nullable=True),
        sa.Column("audio_script", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("artifact_stories")
    op.drop_table("reconstruction_tasks")
    op.drop_table("artifact_models")
    op.drop_table("artifact_images")
    op.drop_table("artifacts")
