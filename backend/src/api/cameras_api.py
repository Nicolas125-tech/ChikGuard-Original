import os
from flask import Blueprint, jsonify, request
from src.security.auth import require_auth

def create_cameras_blueprint(deps):
    bp = Blueprint("cameras_api", __name__)
    
    db = deps.get("db")
    from database import Camera
    guard_critical_action = deps.get("guard_critical_action")

    @bp.route("/api/cameras", methods=["GET"])
    @require_auth()
    def get_cameras():
        cameras = Camera.query.order_by(Camera.created_at.desc()).all()
        return jsonify({"count": len(cameras), "items": [c.to_dict() for c in cameras]})

    @bp.route("/api/cameras", methods=["POST"])
    @require_auth()
    def create_camera():
        ok, resp = guard_critical_action("create_camera", permission="camera.manage")
        if not ok: return resp
        
        data = request.get_json() or {}
        camera_id = data.get("camera_id")
        name = data.get("name")
        
        if not camera_id or not name:
            return jsonify({"msg": "camera_id and name are required"}), 400
            
        if Camera.query.filter_by(camera_id=camera_id).first():
            return jsonify({"msg": "camera_id already exists"}), 400
            
        c = Camera(
            camera_id=camera_id,
            name=name,
            connection_type=data.get("connection_type", "url"),
            connection_url=data.get("connection_url", ""),
            status="offline"
        )
        db.session.add(c)
        db.session.commit()
        return jsonify(c.to_dict()), 201

    @bp.route("/api/cameras/<int:id>", methods=["PUT", "PATCH"])
    @require_auth()
    def update_camera(id):
        ok, resp = guard_critical_action("update_camera", permission="camera.manage")
        if not ok: return resp
        
        c = Camera.query.get(id)
        if not c:
            return jsonify({"msg": "Camera not found"}), 404
            
        data = request.get_json() or {}
        if "name" in data: c.name = data["name"]
        if "connection_type" in data: c.connection_type = data["connection_type"]
        if "connection_url" in data: c.connection_url = data["connection_url"]
        if "status" in data: c.status = data["status"]
        
        db.session.commit()
        return jsonify(c.to_dict())

    @bp.route("/api/cameras/<int:id>", methods=["DELETE"])
    @require_auth()
    def delete_camera(id):
        ok, resp = guard_critical_action("delete_camera", permission="camera.manage")
        if not ok: return resp
        
        c = Camera.query.get(id)
        if not c:
            return jsonify({"msg": "Camera not found"}), 404
            
        db.session.delete(c)
        db.session.commit()
        return jsonify({"msg": "Camera deleted"})

    return bp

