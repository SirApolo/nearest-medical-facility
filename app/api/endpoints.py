from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast
from geoalchemy2 import Geography
from app.db.database import get_db
from app.models.unit import HealthcareUnit, WGS84_SRID
from app.schemas.unit import HealthcareUnitResponse

DEFAULT_SEARCH_RADIUS_METERS = 5000
MAX_RESULTS_LIMIT = 50

router = APIRouter(prefix="/units", tags=["units"])

@router.get("/nearby", response_model=list[HealthcareUnitResponse])
def get_nearby_units(
    lat: float = Query(..., description="Latitude of the center point"),
    lon: float = Query(..., description="Longitude of the center point"),
    radius: float = Query(DEFAULT_SEARCH_RADIUS_METERS, description="Search radius in meters"),
    db: Session = Depends(get_db)
):
    """
    Find healthcare units within a specific radius using PostGIS ST_DWithin.
    SRID 4326 is cast to Geography for meter-based distance calculations.
    """
    # Create point WKT
    point = f'SRID={WGS84_SRID};POINT({lon} {lat})'
    
    # Query using geography cast for accurate distance measurements in meters
    query = db.query(HealthcareUnit).filter(
        func.ST_DWithin(
            cast(HealthcareUnit.geom, Geography),
            func.ST_GeographyFromText(point),
            radius
        )
    ).limit(MAX_RESULTS_LIMIT).all()
    
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
