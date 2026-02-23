from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models.unit import HealthcareUnit
from app.schemas.unit import HealthcareUnitResponse

router = APIRouter(prefix="/units", tags=["units"])

@router.get("/nearby", response_model=list[HealthcareUnitResponse])
def get_nearby_units(
    lat: float = Query(..., description="Latitude of the center point"),
    lon: float = Query(..., description="Longitude of the center point"),
    radius: float = Query(5000, description="Search radius in meters"),
    db: Session = Depends(get_db)
):
    """
    Find healthcare units within a specific radius using PostGIS ST_DWithin.
    SRID 4326 is cast to Geography for meter-based distance calculations.
    """
    # Create point WKT
    point = f'SRID=4326;POINT({lon} {lat})'
    
    # Query using geography cast for accurate distance measurements in meters
    query = db.query(HealthcareUnit).filter(
        func.ST_DWithin(
            func.cast(HealthcareUnit.geom, func.geography()),
            func.cast(func.ST_GeomFromEWKT(point), func.geography()),
            radius
        )
    ).limit(50).all()
    
    return query

@router.get("/{cnes_id}", response_model=HealthcareUnitResponse)
def get_unit(cnes_id: str, db: Session = Depends(get_db)):
    """
    Get a specific healthcare unit by its CNES ID.
    """
    unit = db.query(HealthcareUnit).filter(HealthcareUnit.cnes_id == cnes_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Healthcare unit not found")
    return unit
