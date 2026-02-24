# Healthcare Spatial Intelligence API - Brazil

## 1. Project Overview
The Healthcare Spatial Intelligence API is a professional, high-performance backend system built to process, store, and serve geospatial data related to Brazilian healthcare facilities. It integrates directly with Brazil's official health data portal (DATASUS), specifically targeting the National Register of Healthcare Facilities (CNES). Through advanced spatial queries, this platform allows clients to effortlessly locate nearby hospitals, clinics, and health units within a specified radius.

## 2. Tech Stack
This project leverages a modern, robust technology stack, engineered for high performance, spatial accuracy, and maintainability:

*   **FastAPI:** The core web framework. Chosen for its extreme speed, asynchronous capabilities, and automatic generation of interactive API documentation (Swagger UI).
*   **PostgreSQL & PostGIS:** The relational database system, extended with PostGIS for advanced geospatial capabilities. It stores healthcare facilities as accurate geographical points (SRID 4326), enabling precise, meter-based radius searches.
*   **Docker & Docker Compose:** Containerization tools used to isolate environments, ensure reproducible builds, and seamlessly orchestrate both the API and Database services.
*   **SQLAlchemy & GeoAlchemy2:** The Object-Relational Mapping (ORM) layer, ensuring secure and pythonic interactions with spatial data.
*   **Pandas:** Used in the ETL pipeline for efficient, memory-safe data extraction and transformation of large CSV datasets.
*   **Python 3.10+:** Leveraging modern language features, strict built-in type hints (`list`, `dict`, `| None`), and adherence to **PEP 8** coding standards for clean, maintainable, and enterprise-grade code.

## 3. Project Structure
The repository is modularized for scalable API expansion and clear separation of concerns:

```text
├── app
│   ├── api          # FastAPI routers and RESTful endpoints
│   ├── db           # Database connection engines and session generation
│   ├── ingestion    # Data loaders, chunked processing, and raw CNES AWS S3 integration
│   ├── models       # SQLAlchemy ORM and GeoAlchemy2 spatial models
│   ├── schemas      # Pydantic models for request/response serialization (strict parsing)
│   └── main.py      # Entry point for the FastAPI application server
├── docker-compose.yml # Orchestration configuration for local development
├── Dockerfile       # Container blueprint for the FastAPI server build
├── requirements.txt
└── README.md
```

## 4. Architecture Diagram Description
*Note: A visual diagram could be placed here. Below is the architectural flow description.*

1.  **Data Source (DATASUS S3):** The official Brazilian health open data portal hosts the raw CNES CSV datasets directly on AWS S3.
2.  **ETL Pipeline (Ingestion Engine):** A manually triggered Python script (`app/ingestion/cnes_loader.py`) streams the zipped dataset, cleans anomalies, transforms coordinate systems, and maps the schema dynamically using `pandas`.
3.  **Database Layer (PostGIS):** Transformed geographic entities are digested into the `healthcare_units` relational table as WKT `POINT` geometries.
4.  **Application Layer (FastAPI):** Exposes RESTful endpoints leveraging dependency injection (session management) to execute fast spatial SQL queries.
5.  **Client/Consumer:** Front-end applications, mobile apps, or data scientists consume the API, receiving clean, serialized JSON payloads (via Pydantic).

## 5. How to Run with Docker Compose
The application is entirely containerized for a friction-free development and deployment experience.

### Step 1: Spin up the Services
Build and start the PostgreSQL (PostGIS) database and the FastAPI web server in detached mode:
```bash
docker-compose up --build -d
```
*The API interactive documentation will be instantly available at [http://localhost:8000/docs](http://localhost:8000/docs).*

### Step 2: Trigger the ETL Pipeline
With the containers running, execute the data ingestion script inside the API container to extract, transform, and load real national facilities data into the database:
```bash
# Ingest all national health units
docker-compose exec api python -m app.ingestion.cnes_loader

# Or optionally, ingestion by a specific state code (e.g., 41 for Paraná)
docker-compose exec api python -m app.ingestion.cnes_loader --state 41
```

## 6. Key Features & Best Practices

*   **Geospatial Queries (ST_DWithin):** Utilizes `geoalchemy2` and PostGIS to perform highly accurate radius searches. By casting `geometry` to `geography` types during query execution, distances are calculated dynamically in exact meters rather than raw continuous degrees.
*   **Automated ETL Pipeline:** The data loader is designed to prevent RAM exhaustion when handling hundreds of thousands of DATASUS records. It parses large CSV streams using controlled, dynamic memory chunks.
*   **Professional Code Standards:**
    *   **Strict Type Hinting:** Comprehensive usage of Python 3.10+ native type hints (e.g., `list`, `float | None`) to catch errors at compile-time and improve IDE intellisense.
    *   **PEP 8 Compliance:** Strictly follows Python Enhancement Proposal 8 for clean code formatting and structured imports.
    *   **Data Serialization/Validation:** Pydantic schemas enforce strict input validations and output payload structures.
    *   **Dependency Injection:** Secure and decoupled database session generation (`get_db`) injected directly into FastAPI router dependencies.

## 7. API Endpoints

The API interactive Swagger UI documentation is available at `/docs`. Below is a quick manual reference:

*   **`GET /units/nearby`**
    *   **Purpose:** Finds healthcare units near the specified location utilizing the `ST_DWithin` function.
    *   **Parameters:** `lat` (latitude), `lon` (longitude), `radius` (search radius in exact meters).
    *   **Returns:** A serialized list of strict JSON objects matching the `HealthcareUnitResponse` Pydantic schema.
*   **`GET /units/{cnes_id}`**
    *   **Purpose:** Retrieves comprehensive details about a specific facility utilizing the unique CNES ID index.
    *   **Returns:** A single strict JSON object representing the unit's metadata and exact geographic properties.
