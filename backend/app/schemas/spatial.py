from typing import Dict, Any
import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
    computed_field,
)
from shapely.geometry import shape

# Country constants mapping site code prefixes to countries
COUNTRIES = {
    "SIO": "Kenya",
    "MS1": "Tanzania",
}


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
    code: str = Field(
        ...,
        max_length=50,
        description=(
            "Unique alphanumeric identifier code for the monitoring site"
        ),
    )
    wetland_id: uuid.UUID = Field(
        ..., description="Unique identifier of the associated wetland"
    )
    name: str = Field(
        ...,
        max_length=150,
        description="Human-readable name of the monitoring site",
    )
    description: str | None = Field(
        default=None,
        description="Optional text description of the monitoring site",
    )
    geom: Dict[str, Any] = Field(
        ..., description="GeoJSON Point geometry representation of the site"
    )

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


class SiteUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        max_length=50,
        description=(
            "Unique alphanumeric identifier code for the monitoring site"
        ),
    )
    wetland_id: uuid.UUID | None = Field(
        default=None, description="Unique identifier of the associated wetland"
    )
    name: str | None = Field(
        default=None,
        max_length=150,
        description="Human-readable name of the monitoring site",
    )
    description: str | None = Field(
        default=None,
        description="Optional text description of the monitoring site",
    )
    geom: Dict[str, Any] | None = Field(
        default=None,
        description="GeoJSON Point geometry representation of the site",
    )

    @field_validator("geom", mode="before")
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

    @field_validator("geom")
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


class ManagementActionResponse(BaseModel):
    label: str = Field(
        ...,
        validation_alias="short_label",
        description="Label/title of the recommended management action",
    )
    description: str = Field(
        ...,
        validation_alias="description_text",
        description="Detailed description of the management action",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MetricEntryResponse(BaseModel):
    value: Any
    unit: str | None = None
    status: str = "Normal"
    label: str
    icon: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupScoreEntryResponse(BaseModel):
    score: float
    label: str
    icon: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FgdSignalDetails(BaseModel):
    fish_abundance: str = "Same"
    water_clarity: str = "Same"
    vegetation_cover: str = "Same"
    pollution_events: str = "None"
    encoded_signal_value: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class SiteStatus(BaseModel):
    composite_score: float = Field(
        ...,
        description="Composite wetland health score (normalized 0.0 to 1.0)",
    )
    ik_adjusted_score: float = Field(
        ...,
        description=(
            "Fuzzy-adjusted composite score after integrating "
            "Indigenous Knowledge (normalized 0.0 to 1.0)"
        ),
    )
    traffic_light: str = Field(
        ...,
        description="Visual status traffic light indicator (GREEN, YELLOW, RED)",  # noqa
    )
    health_class: str = Field(
        ...,
        description=(
            "WHO-aligned wetland health class (A=Excellent, B=Good, "
            "C=Fair, D=Poor, E=Critical)"
        ),
    )
    sampling_date: datetime | None = Field(
        default=None,
        description="Timestamp of the latest sampling record",
    )
    metrics: dict[str, MetricEntryResponse] = Field(
        default_factory=dict,
        description="Map of dynamic parameters collected at this site",
    )
    score_breakdown: dict[str, GroupScoreEntryResponse] = Field(
        default_factory=dict,
        description="Map of dynamic parameter group scores",
    )
    ik_signal: FgdSignalDetails | None = Field(
        default=None,
        description="Detailed FGD community signal scores",
    )

    model_config = ConfigDict(from_attributes=True)


class Site(SiteBase):
    id: uuid.UUID
    status: SiteStatus | None = None
    management_actions: list[ManagementActionResponse] = []
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def country(self) -> str:
        prefix = (
            self.code.split("-")[0].upper()
            if "-" in self.code
            else self.code.upper()
        )
        return COUNTRIES.get(prefix, "Tanzania")


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
    id: uuid.UUID = Field(
        ..., description="Unique identifier of the score history entry"
    )
    site_id: uuid.UUID = Field(
        ..., description="Unique identifier of the associated monitoring site"
    )
    wqi_score: Decimal = Field(
        ..., description="Water Quality Index score (normalized 0.0 to 1.0)"
    )
    composite_score: Decimal = Field(
        ...,
        description="Composite wetland health score (normalized 0.0 to 1.0)",
    )
    ik_signal_value: Decimal = Field(
        ...,
        description="Indigenous Knowledge signal value (normalized 0.0 to 1.0)",  # noqa
    )
    adjusted_score: Decimal = Field(
        ...,
        description=(
            "Fuzzy-adjusted composite score after integrating "
            "Indigenous Knowledge (normalized 0.0 to 1.0)"
        ),
    )
    health_class: str = Field(
        ...,
        description=(
            "WHO-aligned wetland health class (A=Excellent, B=Good, "
            "C=Fair, D=Poor, E=Critical)"
        ),
    )
    calculated_at: datetime = Field(
        ..., description="Timestamp when the scores were calculated"
    )

    model_config = ConfigDict(from_attributes=True)
