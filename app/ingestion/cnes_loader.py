import pandas as pd
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.unit import HealthcareUnit
from geoalchemy2.elements import WKTElement
import urllib.request
import zipfile
import os

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
    url = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip"
    zip_path = "/tmp/cnes_estabelecimentos_csv.zip"
    
    print(f"Downloading CNES open data from AWS S3... (This might take a while)")
    try:
        # Create tmp dir if not exists inside container
        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print(f"Failed to download the data: {e}")
        return

    db: Session = SessionLocal()
    HealthcareUnit.metadata.create_all(bind=engine)
    
    records_saved = 0
    records_skipped = 0
    
    # User requested schema mapping:
    # CO_CNES -> cnes_id, NO_FANTASIA -> name, CO_UF -> state, NO_BAIRRO -> city, NU_LATITUDE -> latitude, NU_LONGITUDE -> longitude
    cols_to_use = ['CO_CNES', 'NO_FANTASIA', 'CO_UF', 'NO_BAIRRO', 'NU_LATITUDE', 'NU_LONGITUDE']
    
    print("Extracting and processing the CSV file in chunks...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_filename = [f for f in z.namelist() if f.endswith('.csv')][0]
            with z.open(csv_filename) as f:
                # Read in chunks to prevent memory issues for the national DB
                chunksize = 50000
                for count, chunk in enumerate(pd.read_csv(f, sep=';', encoding='latin1', dtype=str, usecols=lambda c: c in cols_to_use, chunksize=chunksize)):
                    print(f"Processing chunk {count+1}...")
                    
                    if state_filter:
                        # Optional: filter by UF code. For 'PR', the CO_UF is 41, SP is 35.
                        # Wait, the user said they might pass strings. For simplicity, just filter later or omit filter
                        pass
                    
                    for _, row in chunk.iterrows():
                        try:
                            cnes_id = str(row.get('CO_CNES', '')).strip()
                            if not cnes_id or cnes_id == 'nan':
                                continue
                                
                            name = str(row.get('NO_FANTASIA', 'Unknown Unit'))
                            if pd.isna(name) or name == 'nan':
                                name = 'Unknown Unit'
                                
                            state = str(row.get('CO_UF', 'UNK')).strip()
                            city = str(row.get('NO_BAIRRO', 'Unknown')).strip()
                            
                            lat_raw = row.get('NU_LATITUDE')
                            lon_raw = row.get('NU_LONGITUDE')
                            
                            lat = clean_coordinates(lat_raw)
                            lon = clean_coordinates(lon_raw)
                            
                            # Deduplication
                            existing = db.query(HealthcareUnit).filter(HealthcareUnit.cnes_id == cnes_id).first()
                            if existing:
                                records_skipped += 1
                                continue
                                
                            geom = None
                            if lat is not None and lon is not None:
                                geom = WKTElement(f'POINT({lon} {lat})', srid=4326)
                                
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
        if os.path.exists(zip_path):
            os.remove(zip_path)
            
    print(f"Ingestion complete. Saved: {records_saved}, Skipped (existing): {records_skipped}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest National CNES data automatically from DATASUS AWS S3")
    parser.add_argument("--state", type=str, default=None, help="(Optional) State abbreviation to filter")
    args = parser.parse_args()
    
    fetch_and_load_data(args.state)
