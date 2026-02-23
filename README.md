# Healthcare Spatial Intelligence API - Brazil (FastAPI + PostGIS + PySUS)

A professional Backend API built with **FastAPI** and **PostgreSQL/PostGIS**, tailored for the Brazilian healthcare sector. The platform offers spatial queries and integration with Brazilian open health data (DATASUS).

## Overview
This platform ingests, stores, and serves geospatial data from Brazilian healthcare facilities (CNES - Cadastro Nacional de Estabelecimentos de Saúde). It easily finds nearby hospitals and units within a given radius by utilizing advanced topological functions on PostGIS.

## Project Structure
```text
├── app
│   ├── api          # FastAPI routers and endpoints
│   ├── db           # Database connection and session
│   ├── ingestion    # Data loaders and PySUS integration
│   ├── models       # SQLAlchemy ORM and GeoAlchemy2 models
│   ├── schemas      # Pydantic models for request/response serialization
│   └── main.py      # Entry point for the FastAPI application
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Data Source
The data ingestion pipeline integrates seamlessly with Brazil's **DATASUS** open data portal.

The `app/ingestion/cnes_loader.py` script specifically connects to the official AWS S3 bucket (`s3.sa-east-1.amazonaws.com/ckan.saude.gov.br`) to retrieve the most recent complete national `cnes_estabelecimentos_csv.zip` dataset. It streams the archive, parses the data using `pandas` in efficient memory chunks, maps the necessary columns (`CO_CNES`, `NO_FANTASIA`, `CO_UF`, `NO_BAIRRO`, `NU_LATITUDE`, `NU_LONGITUDE`), cleans coordinate anomalies, and seamlessly feeds the local PostGIS instance.

## Technical Challenges
* **Large-scale Geographical Data Processing:** Healthcare data from DATASUS comprises hundreds of thousands of records. Processing strings into spatial coordinates required efficient bulk insertions and chunked memory processing using `pandas` to avoid RAM exhaustion.
* **Spatial Reference System (SRID 4326):** Ensuring the correct projection system is critical. We utilized the **WGS 84 (SRID 4326)** standard to align our database logic with standard GPS latitude and longitude parameters.
* **Accuracy via Geography Casting:** To ensure `ST_DWithin` calculates distances in exact meters (rather than raw degrees), we enforce dynamic casts to PostGIS `geography` types during query execution (`func.cast(geom, func.geography())`).

## How to run

### 1. Start the PostGIS Database and API
The application is entirely containerized. To fire up both the PostgreSQL engine and the FastAPI server, simply use Docker Compose:

```bash
# Build and run the containers in detached mode
docker-compose up --build -d
```

Your API is now available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Run the Data Ingestion Script (CNES Loader)
With both containers running, dispatch the extraction script from inside the API container to automatically download and ingest the national facility data:

```bash
# Load all national data
docker-compose exec api python -m app.ingestion.cnes_loader

# Or optionally, filter by state code (e.g., 41 for PR)
docker-compose exec api python -m app.ingestion.cnes_loader --state 41
```

This will download the national data from the official S3 bucket, parse coordinates into PostGIS geometries, and insert them into the `healthcare_units` table.

## API Endpoints

- `GET /units/nearby?lat={latitude}&lon={longitude}&radius={meters}`: Finds healthcare units near the specified location utilizing the ST_DWithin function.
- `GET /units/{cnes_id}`: Retrieves comprehensive details about a specific facility.
