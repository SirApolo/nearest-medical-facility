from pydantic import BaseModel
from typing import Optional

class HealthcareUnitBase(BaseModel):
    cnes_id: str
    name: str
    state: str
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class HealthcareUnitResponse(HealthcareUnitBase):
    id: int

    class Config:
        from_attributes = True
