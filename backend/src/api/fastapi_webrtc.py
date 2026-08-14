import asyncio
import logging
import time
import uuid

import cv2
import jwt
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from av import VideoFrame
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.state import get_global_frame
from src.security.fastapi_auth import SUPABASE_JWT_SECRET, UserContext, get_current_user

router = APIRouter(prefix="/api/webrtc", tags=["video"])
logger = logging.getLogger(__name__)

relay = MediaRelay()
pcs = set()

class WebRTCOffer(BaseModel):
    sdp: str
    type: str

class GlobalFrameTrack(VideoStreamTrack):
    def __init__(self, fps=30):
        super().__init__()
        self.fps = fps
        self.interval = 1.0 / fps

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        frame = get_global_frame()
        if frame is None:
            # Send a black frame if no frame is available
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Convert BGR (OpenCV) to RGB (WebRTC)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        await asyncio.sleep(self.interval)
        return video_frame

@router.post("/offer")
async def webrtc_offer(offer: WebRTCOffer, user: UserContext = Depends(get_current_user)):
    pc_id = f"PeerConnection({uuid.uuid4()})"
    session_desc = RTCSessionDescription(sdp=offer.sdp, type=offer.type)
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
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)

    track = GlobalFrameTrack()
    pc.addTrack(relay.subscribe(track))

    await pc.setRemoteDescription(session_desc)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": answer.sdp, "type": answer.type}

@router.get("/pcs")
def webrtc_pcs(user: UserContext = Depends(get_current_user)):
    return {"count": len(pcs)}

# --- MJPEG Stream Otmizado ---
@router.get("/video")
def video_feed(token: str = None):
    # JWT validacao embutida ou via middleware para streams GET
    # Como e tag <img src="..."/>, usamos query token na autenticacao
    if not token:
        raise HTTPException(status_code=401, detail="Token JWT requerido")

    try:
        # Validate JWT explicitly for streaming endpoint using query parameter
        jwt_secret = os.environ.get("SUPABASE_JWT_SECRET") or SUPABASE_JWT_SECRET
        jwt.decode(
            token, jwt_secret, algorithms=["HS256"], audience="authenticated"
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token JWT expirado")
    except Exception as e:
        logger.error(f"Erro de autenticacao de video (Token invalido): {str(e)}")
        raise HTTPException(status_code=401, detail="Token JWT invalido")

    async def generate():
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        stream_interval = 1.0 / 30
        try:
            while True:
                t0 = time.perf_counter()
                frame = get_global_frame()
                if frame is not None:
                    ret, buf = cv2.imencode(".jpg", frame, encode_params)
                    if ret:
                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")

                elapsed = time.perf_counter() - t0
                sleep_t = stream_interval - elapsed
                if sleep_t > 0.001:
                    await asyncio.sleep(sleep_t)
        except GeneratorExit:
            pass

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
