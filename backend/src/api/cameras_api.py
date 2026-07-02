from flask import Blueprint, jsonify, request

from src.security.auth import require_auth


def _handle_get_cameras(Camera):
    cameras = Camera.query.order_by(Camera.created_at.desc()).all()
    return jsonify(
        {"count": len(cameras), "items": [c.to_dict() for c in cameras]}
    )


def _handle_create_camera(db, guard_critical_action, Camera):
    ok, resp = guard_critical_action(
        "create_camera", permission="camera.manage"
    )
    if not ok:
        return resp

    data = request.get_json() or {}
    camera_id = data.get("camera_id")
    name = data.get("name")

    if not camera_id or not name:
        return jsonify({"msg": "camera_id and name are required"}), 400

    if (
        len(str(camera_id)) > 50
        or len(str(name)) > 100
        or len(str(data.get("connection_url", ""))) > 500
    ):
        return jsonify({"msg": "Input length limits exceeded"}), 400

    if Camera.query.filter_by(camera_id=camera_id).first():
        return jsonify({"msg": "camera_id already exists"}), 400

    c = Camera(
        camera_id=camera_id,
        name=name,
        connection_type=data.get("connection_type", "url"),
        connection_url=data.get("connection_url", ""),
        status="offline",
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


def _handle_update_camera(id, db, guard_critical_action, Camera):
    ok, resp = guard_critical_action(
        "update_camera", permission="camera.manage"
    )
    if not ok:
        return resp

    c = Camera.query.get(id)
    if not c:
        return jsonify({"msg": "Camera not found"}), 404

    data = request.get_json() or {}

    if (
        len(str(data.get("name", ""))) > 100
        or len(str(data.get("connection_url", ""))) > 500
    ):
        return jsonify({"msg": "Input length limits exceeded"}), 400

    if "name" in data:
        c.name = data["name"]
    if "connection_type" in data:
        c.connection_type = data["connection_type"]
    if "connection_url" in data:
        c.connection_url = data["connection_url"]
    if "status" in data:
        c.status = data["status"]

    db.session.commit()
    return jsonify(c.to_dict())


def _handle_delete_camera(id, db, guard_critical_action, Camera):
    ok, resp = guard_critical_action(
        "delete_camera", permission="camera.manage"
    )
    if not ok:
        return resp

    c = Camera.query.get(id)
    if not c:
        return jsonify({"msg": "Camera not found"}), 404

    db.session.delete(c)
    db.session.commit()
    return jsonify({"msg": "Camera deleted"})


def _handle_switch_camera(guard_critical_action, Camera):
    ok, resp = guard_critical_action(
        "switch_camera", permission="camera.manage"
    )
    if not ok:
        return resp

    data = request.get_json() or {}
    cid = data.get("camera_id")
    if not cid:
        return jsonify({"msg": "Missing camera_id"}), 400
    if len(str(cid)) > 50:
        return jsonify({"msg": "Input length limits exceeded"}), 400

    c = Camera.query.filter_by(camera_id=cid).first()
    if not c:
        return jsonify({"msg": "Camera not found"}), 404

    # We update the global active camera directly in the app namespace
    try:
        import app as main_app
    except ModuleNotFoundError:
        import app_flask_legacy as main_app

    main_app.ACTIVE_CAMERA_ID = cid
    if c.connection_type == "usb":
        try:
            main_app.CAMERA_INDEX = int(
                c.connection_url
            ) if c.connection_url else 0
        except Exception:
            main_app.CAMERA_INDEX = 0
    else:
        main_app.CAMERA_INDEX = c.connection_url or cid

    # Stop the current capture thread if running.
    # The loop will restart it on-demand.
    if getattr(main_app, "_camera_capture", None) is not None:
        try:
            main_app._camera_capture.stop()
        except Exception:
            pass
        main_app._camera_capture = None

    return jsonify(
        {"msg": "Camera switched successfully", "active_camera": cid}
    )


def create_cameras_blueprint(deps):
    bp = Blueprint("cameras_api", __name__)

    db = deps.get("db")
    from database import Camera

    guard_critical_action = deps.get("guard_critical_action")

    @bp.route("/api/cameras", methods=["GET"])
    @require_auth()
    def get_cameras():
        return _handle_get_cameras(Camera)

    @bp.route("/api/cameras", methods=["POST"])
    @require_auth()
    def create_camera():
        return _handle_create_camera(db, guard_critical_action, Camera)

    @bp.route("/api/cameras/<int:id>", methods=["PUT", "PATCH"])
    @require_auth()
    def update_camera(id):
        return _handle_update_camera(id, db, guard_critical_action, Camera)

    @bp.route("/api/cameras/<int:id>", methods=["DELETE"])
    @require_auth()
    def delete_camera(id):
        return _handle_delete_camera(id, db, guard_critical_action, Camera)

    @bp.route("/api/cameras/switch", methods=["POST"])
    @require_auth()
    def switch_camera():
        return _handle_switch_camera(guard_critical_action, Camera)

    return bp
