from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ncrawler.api.auth import require_api_key
from ncrawler.api.dependencies import get_db
from ncrawler.api.schemas import RuleCreate, RuleRead, RuleUpdate
from ncrawler.db.models.rule import RuleModel

router = APIRouter(prefix="/rules", tags=["rules"], dependencies=[Depends(require_api_key)])


def _row_to_schema(row: RuleModel) -> RuleRead:
    return RuleRead(
        id=row.id,
        name=row.name,
        enabled=row.enabled,
        genres=row.genres,
        min_rating=row.min_rating,
        directors=row.directors,
        actors=row.actors,
        studios=row.studios,
        media_type=row.media_type,
        quality_profile=row.quality_profile,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[RuleRead])
def list_rules(db: Session = Depends(get_db)) -> list[RuleRead]:
    rows = db.query(RuleModel).all()
    return [_row_to_schema(r) for r in rows]


@router.post("", response_model=RuleRead, status_code=201)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)) -> RuleRead:
    row = RuleModel(
        name=payload.name,
        enabled=payload.enabled,
        min_rating=payload.min_rating,
        media_type=payload.media_type.value,
        quality_profile=payload.quality_profile,
    )
    row.genres = payload.genres
    row.directors = payload.directors
    row.actors = payload.actors
    row.studios = payload.studios
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_schema(row)


@router.get("/{rule_id}", response_model=RuleRead)
def get_rule(rule_id: int, db: Session = Depends(get_db)) -> RuleRead:
    row = db.get(RuleModel, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _row_to_schema(row)


@router.patch("/{rule_id}", response_model=RuleRead)
def update_rule(rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db)) -> RuleRead:
    row = db.get(RuleModel, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "media_type":
            setattr(row, field, value.value if hasattr(value, "value") else value)
        elif field in ("genres", "directors", "actors", "studios"):
            setattr(row, field, value)
        else:
            setattr(row, field, value)

    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_schema(row)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.get(RuleModel, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(row)
    db.commit()
    return Response(status_code=204)
