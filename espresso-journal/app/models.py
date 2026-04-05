from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


SourceChannel = Literal["web", "telegram", "email", "api"]


class DialEntry(BaseModel):
    roaster: str = Field(..., min_length=1, description="Coffee roaster name")
    roast_style: str = Field(..., min_length=1, description="e.g. light, medium, espresso blend")
    entry_date: date = Field(..., description="Dial session date")
    dose_in_g: float = Field(..., gt=0, description="Dose in basket (g)")
    dose_out_g: float = Field(..., gt=0, description="Yield in cup (g)")
    grind_size: str = Field(..., min_length=1, description="Grind setting or micron reference")
    grinder: str = Field(..., min_length=1, description="Grinder model")
    extraction_time_s: float = Field(..., gt=0, description="Shot time in seconds")
    tasting_notes: str = Field(default="", description="Free-form tasting notes")
    source: SourceChannel = "api"
