"""Spatial boundary service module.

Provides reusable domain queries for administrative spatial boundaries
(Regions, Counties, Sub-Counties, Wards) adhering to SOC, DRY, and SOLID.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.spatial import SpatialBoundary, Basin


def get_root_boundaries(
    db: Session, basin_codes: Optional[List[str]] = None
) -> List[SpatialBoundary]:
    """Fetch root Level 2 spatial boundaries (Counties/Districts)."""
    query = db.query(SpatialBoundary).filter(SpatialBoundary.level == 2)
    if basin_codes:
        query = query.join(Basin).filter(Basin.code.in_(basin_codes))
    return query.order_by(SpatialBoundary.basin_id, SpatialBoundary.name).all()


def get_child_boundaries(db: Session, parent_id: str) -> List[SpatialBoundary]:
    """Fetch child spatial boundaries for a given parent boundary ID."""
    return (
        db.query(SpatialBoundary)
        .filter(SpatialBoundary.parent_id == parent_id)
        .order_by(SpatialBoundary.name)
        .all()
    )


def has_child_boundaries(db: Session, parent_id: str) -> bool:
    """Check if a spatial boundary has child boundaries (non-leaf check)."""
    return (
        db.query(SpatialBoundary.id)
        .filter(SpatialBoundary.parent_id == parent_id)
        .first()
        is not None
    )


def get_boundary_by_id(
    db: Session, boundary_id: str
) -> Optional[SpatialBoundary]:
    """Fetch a single spatial boundary by its UUID string."""
    try:
        return (
            db.query(SpatialBoundary)
            .filter(SpatialBoundary.id == boundary_id)
            .first()
        )
    except Exception:
        return None
