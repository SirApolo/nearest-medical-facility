import pandas as pd
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.unit import HealthcareUnit
from geoalchemy2.elements import WKTElement
from pysus.online_data import CNES

def clean_coordinates(val):
    try:
        if pd.isna(val) or val == 'NaN':
            return None
        val_float = float(val)
        if val_float == 0:
            return None
        return val_float
    except (ValueError, TypeError):
        return None

def fetch_and_load_data(state: str, year: int, month: int):
    print(f"Downloading CNES data for {state} ({year}-{month:02d})... (This might take a while)")
    # 'ST' group stands for Estabelecimentos de Saúde
    df = CNES.download(group='ST', states=state, years=year, months=month).to_dataframe()
    print(f"Downloaded {len(df)} records. Processing data...")
    
    # Identify dynamic columns from pysus return dataframe
    col_cnes = 'CNES' if 'CNES' in df.columns else df.columns[0]
    col_name = 'FANTASIA' if 'FANTASIA' in df.columns else ('NO_FANTASIA' if 'NO_FANTASIA' in df.columns else 'NOME')
    col_lat = 'LATITUDE' if 'LATITUDE' in df.columns else 'NU_LATITUDE'
    col_lon = 'LONGITUDE' if 'LONGITUDE' in df.columns else 'NU_LONGITUD'
    
    db: Session = SessionLocal()
    
    # Ensure tables are created
    HealthcareUnit.metadata.create_all(bind=engine)
    
    records_saved = 0
    records_skipped = 0
    
    for _, row in df.iterrows():
        try:
            cnes_id = str(row.get(col_cnes, '')).strip()
            name = str(row.get(col_name, 'Unknown Unit')).strip()
            
            lat_raw = row.get(col_lat)
            lon_raw = row.get(col_lon)
            
            lat = clean_coordinates(lat_raw)
            lon = clean_coordinates(lon_raw)
            
            # Simple deduplication
            existing = db.query(HealthcareUnit).filter(HealthcareUnit.cnes_id == cnes_id).first()
            if existing:
                records_skipped += 1
                continue
                
            geom = None
            if lat is not None and lon is not None:
                # WKT expects POINT(lon lat)
                geom = WKTElement(f'POINT({lon} {lat})', srid=4326)
                
            unit = HealthcareUnit(
                cnes_id=cnes_id,
                name=name,
                state=state,
                city=str(row.get('CO_MUNICIP', 'Unknown')),
                latitude=lat,
                longitude=lon,
                geom=geom
            )
            
            db.add(unit)
            records_saved += 1
            
            # Commit in batches of 500
            if records_saved % 500 == 0:
                db.commit()
                print(f"Saved {records_saved} records...")
                
        except Exception as e:
            print(f"Error processing row for CNES ID {cnes_id}: {e}")
            db.rollback()
            
    db.commit()
    db.close()
    
    print(f"Ingestion complete. Saved: {records_saved}, Skipped (existing): {records_skipped}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest CNES data from DATASUS via pysus")
    parser.add_argument("--state", type=str, default="PR", help="State abbreviation (e.g., PR)")
    parser.add_argument("--year", type=int, default=2023, help="Year of the dataset")
    parser.add_argument("--month", type=int, default=8, help="Month of the dataset")
    
    args = parser.parse_args()
    fetch_and_load_data(args.state, args.year, args.month)
