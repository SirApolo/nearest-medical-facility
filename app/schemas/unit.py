from pydantic import BaseModel

class HealthcareUnitBase(BaseModel):
    cnes_id: str
    name: str
    state: str
    city: str
    latitude: float | None = None
    longitude: float | None = None

class HealthcareUnitResponse(HealthcareUnitBase):
    id: int

    class Config:
        from_attributes = True
