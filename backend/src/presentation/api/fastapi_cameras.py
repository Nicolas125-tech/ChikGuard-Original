from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.infrastructure.db.session import get_db
from src.security.fastapi_auth import get_current_user, UserContext, RequireRole
from pydantic import BaseModel
from typing import Optional
from database import Camera
import logging

router = APIRouter(prefix="/api/cameras", tags=["cameras"])
logger = logging.getLogger(__name__)

class CameraCreate(BaseModel):
    camera_id: str
    name: str
    connection_type: Optional[str] = "usb"
    connection_url: Optional[str] = ""

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    connection_type: Optional[str] = None
    connection_url: Optional[str] = None
    status: Optional[str] = None

class CameraSwitch(BaseModel):
    camera_id: str

@router.get("")
async def get_cameras(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    cameras = db.query(Camera).order_by(Camera.created_at.desc()).all()
    from src.core.state import active_camera_id
    return {
        "active_camera_id": active_camera_id,
        "count": len(cameras),
        "items": [c.to_dict() for c in cameras]
    }

@router.post("")
async def create_camera(
    data: CameraCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    if len(data.camera_id) > 50 or len(data.name) > 100 or len(data.connection_url or "") > 500:
        raise HTTPException(status_code=400, detail="Input length limits exceeded")

    if db.query(Camera).filter_by(camera_id=data.camera_id).first():
        raise HTTPException(status_code=400, detail="camera_id already exists")

    c = Camera(
        camera_id=data.camera_id,
        name=data.name,
        connection_type=data.connection_type,
        connection_url=data.connection_url or "",
        status="offline",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c.to_dict()

@router.put("/{id}")
@router.patch("/{id}")
async def update_camera(
    id: int,
    data: CameraUpdate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    c = db.query(Camera).get(id)
    if not c:
        raise HTTPException(status_code=404, detail="Camera not found")

    if data.name is not None:
        if len(data.name) > 100:
            raise HTTPException(status_code=400, detail="Input length limits exceeded")
        c.name = data.name
    if data.connection_type is not None:
        c.connection_type = data.connection_type
    if data.connection_url is not None:
        if len(data.connection_url) > 500:
            raise HTTPException(status_code=400, detail="Input length limits exceeded")
        c.connection_url = data.connection_url
    if data.status is not None:
        c.status = data.status

    db.commit()
    db.refresh(c)
    return c.to_dict()

@router.delete("/{id}")
async def delete_camera(
    id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    c = db.query(Camera).get(id)
    if not c:
        raise HTTPException(status_code=404, detail="Camera not found")

    db.delete(c)
    db.commit()
    return {"msg": "Camera deleted"}

@router.post("/switch")
async def switch_camera(
    data: CameraSwitch,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    if len(data.camera_id) > 50:
        raise HTTPException(status_code=400, detail="Input length limits exceeded")

    c = db.query(Camera).filter_by(camera_id=data.camera_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Camera not found")

    import src.core.state as state
    state.active_camera_id = data.camera_id

    return {"msg": "Camera switched successfully", "active_camera": data.camera_id}
