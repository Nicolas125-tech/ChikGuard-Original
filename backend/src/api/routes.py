import asyncio
import logging
import time
import uuid
from threading import Thread

import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from av import VideoFrame
from flask import Blueprint, Response, jsonify, request

from src.security.auth import require_auth

relay = MediaRelay()
logger = logging.getLogger(__name__)

pcs = set()


class GlobalFrameTrack(VideoStreamTrack):
    def __init__(self, get_global_frame, fps=30):
        super().__init__()
        self.get_global_frame = get_global_frame
        self.fps = fps
        self.interval = 1.0 / fps

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame = self.get_global_frame()
        if frame is None:
            # Send a black frame if no frame is available
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Convert BGR (OpenCV) to RGB (WebRTC)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        # Limit frame rate to self.fps
        await asyncio.sleep(self.interval)

        return video_frame


def _start_async_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


webrtc_loop = asyncio.new_event_loop()
webrtc_thread = Thread(target=_start_async_loop, args=(webrtc_loop,), daemon=True)
webrtc_thread.start()


async def _process_offer(offer_sdp, offer_type, pc_id, get_global_frame):
    offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
    pc = RTCPeerConnection()
    pcs.add(pc)

    logger.info("Created %s", pc_id)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)

    track = GlobalFrameTrack(get_global_frame)
    pc.addTrack(relay.subscribe(track))

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return answer


def create_api_blueprint(deps):
    bp = Blueprint("api_routes", __name__)
    get_global_frame = deps.get("get_global_frame")

    # ── /api/video — MJPEG Stream otimizado ─────────────────────────────────
    @bp.route("/api/video", methods=["GET"])
    @require_auth(allow_query_token=True)
    def video_feed():
        """
        Stream MJPEG de alta performance protegido por token JWT.
        """
        stream_interval = deps.get("stream_frame_interval_sec", 1.0 / 30)
        quality = deps.get("stream_jpeg_quality", 80)
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]

        async def generate():
            last_t = time.perf_counter()
            try:
                while True:
                    t0 = time.perf_counter()
                    frame = get_global_frame()

                    if frame is not None:
                        ret, buf = cv2.imencode(".jpg", frame, encode_params)
                        if ret:
                            data = buf.tobytes()
                            yield (
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: " + str(len(data)).encode() + b"\r\n"
                                b"\r\n" + data + b"\r\n"
                            )

                    # Sleep adaptativo: dorme apenas o tempo restante
                    elapsed = time.perf_counter() - t0
                    sleep_t = stream_interval - elapsed
                    if sleep_t > 0.001:
                        await asyncio.sleep(sleep_t)
            except GeneratorExit:
                pass  # cliente desconectou — saida limpa

        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",  # desabilita buffer do Nginx se presente
        }
        return Response(
            generate(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
            headers=headers,
        )

    @bp.route("/api/webrtc/offer", methods=["POST"])
    @require_auth()
    def webrtc_offer():
        params = request.json
        if not params or "sdp" not in params or "type" not in params:
            return jsonify({"error": "Missing sdp or type in request body"}), 400

        pc_id = "PeerConnection(%s)" % uuid.uuid4()

        future = asyncio.run_coroutine_threadsafe(
            _process_offer(params["sdp"], params["type"], pc_id, get_global_frame), webrtc_loop
        )

        try:
            answer = future.result(timeout=10)
            return jsonify({"sdp": answer.sdp, "type": answer.type})
        except Exception as e:
            logger.error("Failed to process offer: %s", str(e))
            return jsonify({"error": "Ocorreu um erro interno ao processar a oferta WebRTC"}), 500

    @bp.route("/api/webrtc/pcs", methods=["GET"])
    @require_auth()
    def webrtc_pcs():
        return jsonify({"count": len(pcs)})

    return bp
