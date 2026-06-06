"""initial_schema

Revision ID: 95e1b58cd16d
Revises: 
Create Date: 2026-06-06 23:17:49.909794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95e1b58cd16d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("genres_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("min_rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("directors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("actors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("studios_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("media_type", sa.String(20), nullable=False, server_default="both"),
        sa.Column("quality_profile", sa.String(20), nullable=False, server_default="1080p"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "titles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("imdb_id", sa.String(20), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("media_type", sa.String(20), nullable=False, server_default="movie"),
        sa.Column("genres_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("directors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("cast_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("studios_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="monitoring"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_titles_tmdb_id", "titles", ["tmdb_id"])

    op.create_table(
        "downloads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title_id", sa.Integer(), sa.ForeignKey("titles.id"), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("magnet_link", sa.Text(), nullable=True),
        sa.Column("info_hash", sa.String(100), nullable=True),
        sa.Column("quality", sa.String(20), nullable=False, server_default="1080p"),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_downloads_info_hash", "downloads", ["info_hash"])


def downgrade() -> None:
    op.drop_table("downloads")
    op.drop_table("titles")
    op.drop_table("rules")
