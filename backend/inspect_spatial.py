from app.database import Base, create_engine
from sqlalchemy.orm import sessionmaker
from app.models.spatial import SpatialBoundary, Basin
from app.seeds.spatial_seeder_helper import seed_spatial

engine = create_engine("postgresql://nbd_user:password@db:5432/nbd_db_test")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- Basins ---")
for b in db.query(Basin).all():
    print(f"Basin: {b.code}, {b.name}")

print("\n--- Level 2 Spatial Boundaries ---")
for sb in db.query(SpatialBoundary).filter(SpatialBoundary.level == 2).all():
    print(
        f"County/District: Name={sb.name}, Basin={sb.basin.code if sb.basin else None}, ParentID={sb.parent_id}, Parent={sb.parent.name if sb.parent else None}"
    )
