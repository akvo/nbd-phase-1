import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class Basin(Base):
    __tablename__ = "basins"

    basin_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    wetlands = relationship(
        "Wetland", back_populates="basin", cascade="all, delete-orphan"
    )


class Wetland(Base):
    __tablename__ = "wetlands"

    wetland_id = Column(String(50), primary_key=True)
    basin_id = Column(
        String(50),
        ForeignKey("basins.basin_id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(150), nullable=False)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)

    basin = relationship("Basin", back_populates="wetlands")
    sites = relationship(
        "Site", back_populates="wetland", cascade="all, delete-orphan"
    )


class Site(Base):
    __tablename__ = "sites"

    site_id = Column(String(50), primary_key=True)
    wetland_id = Column(
        String(50),
        ForeignKey("wetlands.wetland_id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(150), nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)

    wetland = relationship("Wetland", back_populates="sites")


class SpatialBoundary(Base):
    __tablename__ = "spatial_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    basin_id = Column(
        String(50),
        ForeignKey("basins.basin_id", ondelete="CASCADE"),
        nullable=False,
    )
    centroid_geom = Column(Geometry("POINT", srid=4326), nullable=False)
