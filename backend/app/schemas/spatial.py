from typing import Dict, Any
import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from shapely.geometry import shape


class BasinBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    geom: Dict[str, Any]

    @field_validator("geom", mode="before")
    @classmethod
    def preprocess_geom(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping

            return mapping(to_shape(v))
        except Exception:
            return v

    @field_validator("geom")
    @classmethod
    def validate_geom(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        try:
            s = shape(v)
            if s.geom_type != "MultiPolygon":
                raise ValueError("Geometry must be a MultiPolygon")
        except Exception as e:
            raise ValueError(f"Invalid geometry: {str(e)}")
        return v


class BasinCreate(BasinBase):
    pass


class Basin(BasinBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class WetlandBase(BaseModel):
    code: str = Field(..., max_length=50)
    basin_id: uuid.UUID
    name: str = Field(..., max_length=150)
    geom: Dict[str, Any]

    @field_validator("geom", mode="before")
    @classmethod
    def preprocess_geom(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping

            return mapping(to_shape(v))
        except Exception:
            return v

    @field_validator("geom")
    @classmethod
    def validate_geom(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        try:
            s = shape(v)
            if s.geom_type not in ("Polygon", "MultiPolygon"):
                raise ValueError("Geometry must be a Polygon or MultiPolygon")
            if s.geom_type == "Polygon":
                from shapely.geometry import MultiPolygon, mapping

                s = MultiPolygon([s])
                return mapping(s)
        except Exception as e:
            raise ValueError(f"Invalid geometry: {str(e)}")
        return v


class WetlandCreate(WetlandBase):
    pass


class Wetland(WetlandBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class SiteBase(BaseModel):
    code: str = Field(..., max_length=50)
    wetland_id: uuid.UUID
    name: str = Field(..., max_length=150)
    description: str | None = Field(default=None)
    geom: Dict[str, Any]

    @field_validator("geom", mode="before")
    @classmethod
    def preprocess_geom(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping

            return mapping(to_shape(v))
        except Exception:
            return v

    @field_validator("geom")
    @classmethod
    def validate_geom(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        try:
            s = shape(v)
            if s.geom_type != "Point":
                raise ValueError("Geometry must be a Point")
        except Exception as e:
            raise ValueError(f"Invalid geometry: {str(e)}")
        return v


class SiteCreate(SiteBase):
    pass


class ManagementActionResponse(BaseModel):
    label: str = Field(..., validation_alias="short_label")
    description: str = Field(..., validation_alias="description_text")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SiteStatus(BaseModel):
    composite_score: float
    ik_adjusted_score: float
    traffic_light: str
    health_class: str

    model_config = ConfigDict(from_attributes=True)


class Site(SiteBase):
    id: uuid.UUID
    status: SiteStatus | None = None
    management_actions: list[ManagementActionResponse] = []
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SpatialBoundaryBase(BaseModel):
    name: str = Field(..., max_length=100)
    level: int = Field(..., description="1=Region, 2=District, 3=Sub-county")
    parent_id: uuid.UUID | None = Field(
        default=None, description="Parent spatial boundary ID"
    )
    basin_id: uuid.UUID
    centroid_geom: Dict[str, Any] | None = Field(
        default=None, description="Centroid coordinate point"
    )

    @field_validator("centroid_geom", mode="before")
    @classmethod
    def preprocess_geom(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping

            return mapping(to_shape(v))
        except Exception:
            return v

    @field_validator("centroid_geom")
    @classmethod
    def validate_geom(cls, v: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if v is None:
            return None
        try:
            s = shape(v)
            if s.geom_type != "Point":
                raise ValueError("Geometry must be a Point")
        except Exception as e:
            raise ValueError(f"Invalid geometry: {str(e)}")
        return v


class SpatialBoundaryCreate(SpatialBoundaryBase):
    pass


class SpatialBoundary(SpatialBoundaryBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class SiteScoreHistory(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    wqi_score: Decimal
    composite_score: Decimal
    ik_signal_value: Decimal
    adjusted_score: Decimal
    health_class: str
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)
