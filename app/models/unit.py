from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from app.db.database import Base

class HealthcareUnit(Base):
    __tablename__ = "healthcare_units"

    id = Column(Integer, primary_key=True, index=True)
    cnes_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    state = Column(String, nullable=False)
    city = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geom = Column(Geometry(geometry_type='POINT', srid=4326))
