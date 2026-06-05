from typing import Dict, Any
import uuid
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
            if s.geom_type != "Polygon":
                raise ValueError("Geometry must be a Polygon")
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


class Site(SiteBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class SpatialBoundaryBase(BaseModel):
    name: str = Field(..., max_length=100)
    basin_id: uuid.UUID
    centroid_geom: Dict[str, Any]

    @field_validator("centroid_geom", mode="before")
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

    @field_validator("centroid_geom")
    @classmethod
    def validate_geom(cls, v: Dict[str, Any]) -> Dict[str, Any]:
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
