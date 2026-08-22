# Technical Architecture

## Stack
Frontend: Next.js, React, TypeScript, Leaflet
Backend: FastAPI, Python, Pydantic, SQLAlchemy
Database: PostgreSQL + PostGIS
Routing: OSRM
ML: pandas, numpy, scikit-learn, XGBoost
Jobs: Celery + Redis (or scheduled workers for MVP)

## Services
frontend
  -> api
     -> routing -> OSRM
     -> safety -> PostGIS
     -> evidence -> PostGIS
     -> ML -> versioned model
     -> reports -> PostGIS
     -> weather adapter

## Core tables
users
road_segments
safety_observations
safety_reports
facilities
route_requests
route_results
model_versions
data_sources

## Rule
Backend owns safety decisions. Frontend only renders them.
