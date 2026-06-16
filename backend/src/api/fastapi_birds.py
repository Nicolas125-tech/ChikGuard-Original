import time
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.db.session import get_db
from src.core.state import active_camera_id, live_birds, species_counts, weight_state, cv_lock
from src.schemas.birds import BirdsLiveResponse, WeightLiveResponse
from src.security.fastapi_auth import get_current_user, UserContext
from src.core.config import load_settings

# Modelos do DB 
from database import BirdIdentity, BirdSnapshot, BirdTrackPoint, WeightEstimate

router_birds = APIRouter(prefix="/api/birds", tags=["birds"])
router_weight = APIRouter(prefix="/api/weight", tags=["weight"])

# Variavel ambiente migrada - seria melhor vir do config/settings
BIRD_LIVE_TTL_SEC = 5.0

@router_birds.get("/live", response_model=BirdsLiveResponse)
def get_live_birds(user: UserContext = Depends(get_current_user)):
    now = time.time()
    with cv_lock:
        items = [
            {
                "bird_uid": int(bid),
                "confidence": round(float(data["conf"]), 4),
                "bbox": data["box"],
                "track_id": int(data.get("track_id", -1)),
                "last_seen_seconds": round(now - float(data["last_seen"]), 2),
                "species": data.get("species", "bird"),
                "species_label": data.get("species_label", "AVE"),
            }
            for bid, data in live_birds.items()
            if (now - float(data["last_seen"])) <= BIRD_LIVE_TTL_SEC
        ]
    items.sort(key=lambda item: item["bird_uid"])
    return {
        "count": len(items),
        "ttl_seconds": BIRD_LIVE_TTL_SEC,
        "items": items,
        "species_counts": species_counts,
    }

@router_birds.get("/history")
def get_birds_history(
    limit: int = Query(300, ge=1, le=5000), 
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    rows = db.query(BirdSnapshot).order_by(desc(BirdSnapshot.id)).limit(limit).all()
    return [row.to_dict() for row in reversed(rows)]

@router_birds.get("/registry")
def get_birds_registry(
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    rows = db.query(BirdIdentity).order_by(desc(BirdIdentity.last_seen)).limit(limit).all()
    return {"count": len(rows), "items": [row.to_dict() for row in rows]}

@router_birds.get("/path/{bird_uid}")
def get_bird_path(
    bird_uid: int,
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    rows = (
        db.query(BirdTrackPoint)
        .filter(BirdTrackPoint.bird_uid == bird_uid)
        .order_by(desc(BirdTrackPoint.id))
        .limit(limit)
        .all()
    )
    items = [row.to_dict() for row in reversed(rows)]
    return {"bird_uid": bird_uid, "count": len(items), "items": items}

# --- WEIGHT ROUTER ---

@router_weight.get("/live", response_model=WeightLiveResponse)
def weight_live(user: UserContext = Depends(get_current_user)):
    return {
        "camera_id": active_camera_id,
        "avg_weight_g": weight_state.get("avg_weight_g", 0),
        "ideal_weight_g": weight_state.get("ideal_weight_g", 0),
        "count": weight_state.get("count", 0),
        "confidence": weight_state.get("confidence", 0.0),
        "updated_at_epoch": weight_state.get("updated_at", 0.0),
    }

@router_weight.get("/curve")
def weight_curve(
    days: int = Query(21, ge=1, le=120),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    import datetime
    start_dt = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    rows = (
        db.query(WeightEstimate)
        .filter(
            WeightEstimate.camera_id == active_camera_id, 
            WeightEstimate.timestamp >= start_dt
        )
        .order_by(WeightEstimate.timestamp.asc())
        .all()
    )
    points = [r.to_dict() for r in rows]
    return {"count": len(points), "items": points}
