import pandas as pd
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.unit import HealthcareUnit
from geoalchemy2.elements import WKTElement
import urllib.request
import zipfile
import os

# --- Configuration Constants ---
CNES_S3_URL = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip"
LOCAL_ZIP_PATH = "/tmp/cnes_estabelecimentos_csv.zip"
CSV_CHUNK_SIZE = 50000
WGS84_SRID = 4326

# --- Data Columns Mapping ---
COL_CNES = 'CO_CNES'
COL_NAME = 'NO_FANTASIA'
COL_STATE = 'CO_UF'
COL_CITY = 'NO_BAIRRO'
COL_LAT = 'NU_LATITUDE'
COL_LON = 'NU_LONGITUDE'

def clean_coordinates(val):
    try:
        if pd.isna(val) or val == 'NaN' or str(val).strip() == '':
            return None
        # Handle Brazilian format if necessary
        val_str = str(val).replace(',', '.')
        val_float = float(val_str)
        if val_float == 0:
            return None
        return val_float
    except (ValueError, TypeError):
        return None

def fetch_and_load_data(state_filter=None):
    print(f"Downloading CNES open data from AWS S3... (This might take a while)")
    try:
        # Create tmp dir if not exists inside container
        os.makedirs(os.path.dirname(LOCAL_ZIP_PATH), exist_ok=True)
        urllib.request.urlretrieve(CNES_S3_URL, LOCAL_ZIP_PATH)
    except Exception as e:
        print(f"Failed to download the data: {e}")
        return

    db: Session = SessionLocal()
    HealthcareUnit.metadata.create_all(bind=engine)
    
    records_saved = 0
    records_skipped = 0
    
    # User requested schema mapping converted to usage columns
    cols_to_use = [COL_CNES, COL_NAME, COL_STATE, COL_CITY, COL_LAT, COL_LON]
    
    print("Extracting and processing the CSV file in chunks...")
    try:
        with zipfile.ZipFile(LOCAL_ZIP_PATH, 'r') as z:
            csv_filename = [f for f in z.namelist() if f.endswith('.csv')][0]
            with z.open(csv_filename) as f:
                # Read in chunks to prevent memory issues for the national DB
                for count, chunk in enumerate(pd.read_csv(f, sep=';', encoding='latin1', dtype=str, usecols=lambda c: c in cols_to_use, chunksize=CSV_CHUNK_SIZE)):
                    print(f"Processing chunk {count+1}...")
                    
                    if state_filter:
                        # Optional: filter by UF code. For 'PR', the CO_UF is 41, SP is 35.
                        pass
                    
                    for _, row in chunk.iterrows():
                        try:
                            cnes_id = str(row.get(COL_CNES, '')).strip()
                            if not cnes_id or cnes_id == 'nan':
                                continue
                                
                            name = str(row.get(COL_NAME, 'Unknown Unit'))
                            if pd.isna(name) or name == 'nan':
                                name = 'Unknown Unit'
                                
                            state = str(row.get(COL_STATE, 'UNK')).strip()
                            city = str(row.get(COL_CITY, 'Unknown')).strip()
                            
                            lat_raw = row.get(COL_LAT)
                            lon_raw = row.get(COL_LON)
                            
                            lat = clean_coordinates(lat_raw)
                            lon = clean_coordinates(lon_raw)
                            
                            # Deduplication
                            existing = db.query(HealthcareUnit).filter(HealthcareUnit.cnes_id == cnes_id).first()
                            if existing:
                                records_skipped += 1
                                continue
                                
                            geom = None
                            if lat is not None and lon is not None:
                                geom = WKTElement(f'POINT({lon} {lat})', srid=WGS84_SRID)
                                
                            unit = HealthcareUnit(
                                cnes_id=cnes_id,
                                name=name.strip(),
                                state=state,
                                city=city,
                                latitude=lat,
                                longitude=lon,
                                geom=geom
                            )
                            
                            db.add(unit)
                            records_saved += 1
                            
                            if records_saved > 0 and records_saved % 1000 == 0:
                                db.commit()
                                print(f"Saved {records_saved} records...")
                                
                        except Exception as e:
                            print(f"Error processing row for CNES ID {cnes_id}: {e}")
                            db.rollback()
                            
                    db.commit()
    except Exception as e:
        print(f"Error processing CSV: {e}")
        db.rollback()
    finally:
        db.close()
        if os.path.exists(LOCAL_ZIP_PATH):
            os.remove(LOCAL_ZIP_PATH)
            
    print(f"Ingestion complete. Saved: {records_saved}, Skipped (existing): {records_skipped}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest National CNES data automatically from DATASUS AWS S3")
    parser.add_argument("--state", type=str, default=None, help="(Optional) State abbreviation to filter")
    args = parser.parse_args()
    
    fetch_and_load_data(args.state)
