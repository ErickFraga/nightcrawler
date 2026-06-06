from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ncrawler.api.auth import require_api_key
from ncrawler.api.dependencies import get_db
from ncrawler.api.schemas import DownloadRead, DownloadUpdate
from ncrawler.db.models.download import DownloadModel

router = APIRouter(prefix="/downloads", tags=["downloads"], dependencies=[Depends(require_api_key)])


def _to_schema(row: DownloadModel) -> DownloadRead:
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


@router.get("", response_model=list[DownloadRead])
def list_downloads(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[DownloadRead]:
    query = db.query(DownloadModel)
    if status:
        query = query.filter(DownloadModel.status == status)
    return [_to_schema(r) for r in query.all()]


@router.patch("/{download_id}", response_model=DownloadRead)
def update_download(
    download_id: int,
    payload: DownloadUpdate,
    db: Session = Depends(get_db),
) -> DownloadRead:
    row = db.get(DownloadModel, download_id)
    if not row:
        raise HTTPException(status_code=404, detail="Download not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return _to_schema(row)
