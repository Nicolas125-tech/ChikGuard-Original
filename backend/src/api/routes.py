import uuid
import logging
import asyncio
import cv2
import time
from threading import Thread
from flask import Blueprint, Response, request, jsonify
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from av import VideoFrame
import numpy as np

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

    # We maintain a fallback /api/video for clients not updated yet.
    @bp.route("/api/video", methods=["GET"])
    def video_feed():
        def generate():
            stream_interval = deps.get("stream_frame_interval_sec", 1.0/30)
            quality = deps.get("stream_jpeg_quality", 82)
            while True:
                frame = get_global_frame()
                if frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                time.sleep(stream_interval)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @bp.route("/api/webrtc/offer", methods=["POST"])
    def webrtc_offer():
        params = request.json
        if not params or "sdp" not in params or "type" not in params:
            return jsonify({"error": "Missing sdp or type in request body"}), 400

        pc_id = "PeerConnection(%s)" % uuid.uuid4()

        future = asyncio.run_coroutine_threadsafe(
            _process_offer(params["sdp"], params["type"], pc_id, get_global_frame),
            webrtc_loop
        )

        try:
            answer = future.result(timeout=10)
            return jsonify({
                "sdp": answer.sdp,
                "type": answer.type
            })
        except Exception as e:
            logger.error("Failed to process offer: %s", e)
            return jsonify({"error": str(e)}), 500

    @bp.route("/api/webrtc/pcs", methods=["GET"])
    def webrtc_pcs():
        return jsonify({"count": len(pcs)})

    return bp
