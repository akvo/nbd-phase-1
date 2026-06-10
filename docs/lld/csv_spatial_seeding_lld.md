# Low-Level Design (LLD) — CSV Spatial Seeding

## 1. CSV Data Structure & Parsing
We will parse files:
* `backend/app/seeds/spatial/Mara-sub-counties.csv`
* `backend/app/seeds/spatial/Sio-sub-counties.csv`

Each file has the header:
```csv
id,County,Sub-County
```

## 2. Hierarchical Insertion Strategy
1. **Level 1 (Regions)**: `Mara Region` and `Sio-Siteko Region` must be seeded first (as defined in `spatial_data.json` or fallback).
2. **Level 2 (Counties)**: Read unique counties from the CSV files. Look up or create them as Level 2 boundaries, setting the parent to the corresponding Level 1 Region (`Mara Region` for Mara, `Sio-Siteko Region` for Sio).
3. **Level 3 (Sub-Counties)**: Read sub-counties from each line. Look up their parent County (Level 2) in the database, and insert them as Level 3 boundaries.

## 3. Centroid Coordinates Logic
Since counties and sub-counties lack coordinates in the CSV files, and `centroid_geom` is made nullable in the database schema:
* CSV entries will be seeded with `centroid_geom` set to `None` (NULL).
* Traditional JSON-sourced Region records will retain their explicitly specified centroids.

## 4. DB Session & Commits
* Implement parsing inside `backend/app/seeds/spatial_seeder_helper.py`.
* Wrap insertion logic in transaction blocks and commit at the end.
