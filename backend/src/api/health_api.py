import psutil
import time
from flask import Blueprint, jsonify
from src.security.auth import require_auth
from src.database import db

boot_time = time.time()

def create_health_blueprint(deps):
    bp = Blueprint("health_api", __name__)

    @bp.route("/api/health/system", methods=["GET"])
    @require_auth()
    def system_health():
        # Coletar uso de CPU (intervalo de 0.1s de bloqueio para precisão)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memória
        mem = psutil.virtual_memory()
        
        # Disco
        disk = psutil.disk_usage('/')
        
        # Uptime
        uptime = time.time() - boot_time
        
        # Status do DB
        db_status = "Online"
        try:
            db.session.execute("SELECT 1")
        except Exception:
            db_status = "Offline"
            
        # Status da Câmera / Pipeline
        # 'deps' geralmente contém referências úteis
        cv_status = "Online" if deps.get("get_global_frame") is not None else "Offline"
        
        return jsonify({
            "cpu": cpu_percent,
            "memory": mem.percent,
            "memory_total": mem.total,
            "memory_used": mem.used,
            "disk": disk.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "uptime_seconds": uptime,
            "database": db_status,
            "cv_pipeline": cv_status
        })
        
    return bp
