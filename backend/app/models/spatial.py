import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class BoundaryLevel(int, enum.Enum):
    REGION = 1  # Province / Region
    DISTRICT = 2  # District / County / Kabupaten
    SUB_COUNTY = 3  # Sub-county / Parish / Kecamatan


class Basin(Base):
    __tablename__ = "basins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    wetlands = relationship(
        "Wetland", back_populates="basin", cascade="all, delete-orphan"
    )


class Wetland(Base):
    __tablename__ = "wetlands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    basin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("basins.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(150), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    basin = relationship("Basin", back_populates="wetlands")
    sites = relationship(
        "Site", back_populates="wetland", cascade="all, delete-orphan"
    )


class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    wetland_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wetlands.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(150), nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)

    wetland = relationship("Wetland", back_populates="sites")


class SpatialBoundary(Base):
    __tablename__ = "spatial_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False, index=True)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spatial_boundaries.id", ondelete="CASCADE"),
        nullable=True,
    )
    basin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("basins.id", ondelete="CASCADE"),
        nullable=False,
    )
    centroid_geom = Column(Geometry("POINT", srid=4326), nullable=False)

    basin = relationship("Basin")
    parent = relationship(
        "SpatialBoundary", remote_side=[id], backref="children"
    )
