from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TransitionMetric(BaseModel):
    asset_id: str
    lineage_id: str
    parent_id: str = ""
    transform: str = "master"
    pts_ms: int = Field(ge=0)
    luma_delta: float = Field(ge=0, le=1)
    # Relative luminance of the DARKER of the two states. The published
    # general-flash test applies "where the relative luminance of the darker
    # image is below 0.80", so a large swing between two bright images is not a
    # general flash. Defaults to 0 so older payloads keep their meaning: 0 is
    # below the ceiling, which is the permissive-to-the-rule reading.
    luma_min: float = Field(default=0.0, ge=0, le=1)
    red_delta: float = Field(ge=0, le=1)
    changed_area_fraction: float = Field(ge=0, le=1)
    direction: Literal["up", "down", "flat"]


class Violation(BaseModel):
    asset_id: str
    lineage_id: str
    parent_id: str
    transform: str
    window_start_ms: int
    window_end_ms: int
    rule: Literal["general_flash", "red_flash", "regular_pattern"]
    transitions: int
    peak_changed_area_fraction: float


class Regression(BaseModel):
    child: Violation
    matched_parent: bool
    attribution: str
