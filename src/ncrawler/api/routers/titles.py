from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ncrawler.api.auth import require_api_key
from ncrawler.api.dependencies import get_db
from ncrawler.api.schemas import DownloadCreate, DownloadRead, TitleCreate, TitleRead
from ncrawler.db.models.download import DownloadModel
from ncrawler.db.models.title import TitleModel

router = APIRouter(prefix="/titles", tags=["titles"], dependencies=[Depends(require_api_key)])


def _title_to_schema(row: TitleModel) -> TitleRead:
    return TitleRead(
        id=row.id,
        tmdb_id=row.tmdb_id,
        imdb_id=row.imdb_id,
        title=row.title,
        year=row.year,
        media_type=row.media_type,
        genres=row.genres,
        rating=row.rating,
        directors=row.directors,
        cast=row.cast,
        studios=row.studios,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _download_to_schema(row: DownloadModel) -> DownloadRead:
    return DownloadRead(
        id=row.id,
        title_id=row.title_id,
        source=row.source,
        magnet_link=row.magnet_link,
        info_hash=row.info_hash,
        quality=row.quality,
        status=row.status,
        file_path=row.file_path,
        created_at=row.created_at,
    )


@router.get("", response_model=list[TitleRead])
def list_titles(
    status: Optional[str] = None,
    media_type: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[TitleRead]:
    query = db.query(TitleModel)
    if status:
        query = query.filter(TitleModel.status == status)
    if media_type:
        query = query.filter(TitleModel.media_type == media_type)
    return [_title_to_schema(r) for r in query.all()]


@router.post("", response_model=TitleRead, status_code=201)
def create_title(payload: TitleCreate, db: Session = Depends(get_db)) -> TitleRead:
    row = TitleModel(
        tmdb_id=payload.tmdb_id,
        imdb_id=payload.imdb_id,
        title=payload.title,
        year=payload.year,
        media_type=payload.media_type.value,
        rating=payload.rating,
        status="monitoring",
    )
    row.genres = payload.genres
    row.directors = payload.directors
    row.cast = payload.cast
    row.studios = payload.studios
    db.add(row)
    db.commit()
    db.refresh(row)
    return _title_to_schema(row)


@router.get("/{title_id}", response_model=TitleRead)
def get_title(title_id: int, db: Session = Depends(get_db)) -> TitleRead:
    row = db.get(TitleModel, title_id)
    if not row:
        raise HTTPException(status_code=404, detail="Title not found")
    return _title_to_schema(row)


@router.post("/{title_id}/downloads", response_model=DownloadRead, status_code=201)
def create_download(
    title_id: int,
    payload: DownloadCreate,
    db: Session = Depends(get_db),
) -> DownloadRead:
    title_row = db.get(TitleModel, title_id)
    if not title_row:
        raise HTTPException(status_code=404, detail="Title not found")

    download = DownloadModel(
        title_id=title_id,
        source=payload.source,
        magnet_link=payload.magnet_link,
        info_hash=payload.info_hash,
        quality=payload.quality,
        status="queued",
    )
    db.add(download)

    title_row.status = "found"
    db.commit()
    db.refresh(download)
    return _download_to_schema(download)
