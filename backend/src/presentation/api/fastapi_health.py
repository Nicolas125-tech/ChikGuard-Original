import time
import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.infrastructure.db.session import get_db
from src.security.fastapi_auth import get_current_user, UserContext
from src.core import state

router = APIRouter(prefix="/api/health", tags=["health"])

# Tempo de boot global
boot_time = time.time()

@router.get("/system")
def system_health(
    db: Session = Depends(get_db), 
    user: UserContext = Depends(get_current_user)
):
    """Retorna o status de saude e telemetria do Edge Node ChikGuard."""
    # Uso de CPU (usar psutil.cpu_percent sem block se possivel, ou block curto)
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # Memoria
    mem = psutil.virtual_memory()
    
    # Disco
    disk = psutil.disk_usage("/")
    
    # Uptime
    uptime = time.time() - boot_time
    
    # Status do DB (Validacao ativa)
    db_status = "Online"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "Offline"
        
    cv_status = "Offline" if state.get_global_frame is state._default_get_global_frame else "Online"
    
    return {
        "cpu": cpu_percent,
        "memory": mem.percent,
        "memory_total": mem.total,
        "memory_used": mem.used,
        "disk": disk.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "uptime_seconds": uptime,
        "database": db_status,
        "cv_pipeline": cv_status,
    }
