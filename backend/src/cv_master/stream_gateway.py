import os
import subprocess
import threading
import logging
import tempfile
import time
from flask import Blueprint, send_from_directory

class HLSStreamGateway:
    def __init__(self, fps=30, hls_time=2, hls_list_size=5):
        """
        Gera conteúdo HLS real-time acoplando um subprocesso FFMPEG ao encoder de OpenCV H264.
        Isto elimina a latência massiva e o peso de rede do MJPEG tradicional.
        """
        self.logger = logging.getLogger("cv_master.HLSStreamGateway")
        
        # Cria um diretório temporário persistente para os arquivos de PlayList e Segmentos
        self.hls_dir = tempfile.mkdtemp(prefix="chikguard_hls_")
        self.playlist_path = os.path.join(self.hls_dir, "stream.m3u8")
        
        self.fps = fps
        self.hls_time = hls_time
        self.hls_list_size = hls_list_size
        self.ffmpeg_proc = None
        self.is_running = False
        
        self.blueprint = Blueprint('hls_stream', __name__, url_prefix='/api/stream_sota')
        self._register_routes()

    def start_pipeline(self, width=1280, height=720):
        """
        Inicia o pipe do FFmpeg aguardando frames brutos da nossa Inferência(cv2).
        """
        if self.is_running:
            return

        # Comando Ninja do FFmpeg: Lê rawvideo do stdin (pipe), converte para libx264 ultrafast, 
        # gera HLS em disco e deleta segmentos velhos. 
        command = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f"{width}x{height}",
            '-r', str(self.fps),
            '-i', '-', # Lê do stdin
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p',
            '-g', str(self.fps * 2), # Keyframe a cada 2s
            '-f', 'hls',
            '-hls_time', str(self.hls_time),
            '-hls_list_size', str(self.hls_list_size),
            '-hls_flags', 'delete_segments+append_list',
            '-hls_segment_type', 'mpegts',
            self.playlist_path
        ]
        
        self.logger.info(f"Iniciando HLS FFMPEG Pipe. Saída em: {self.hls_dir}")
        self.ffmpeg_proc = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.is_running = True

    def push_frame(self, frame):
        """
        Injeta o frame matrico (annotated) da master pipeline dentro do FFmpeg.
        """
        if not self.is_running or self.ffmpeg_proc is None or self.ffmpeg_proc.stdin is None:
            return
            
        try:
            self.ffmpeg_proc.stdin.write(frame.tobytes())
        except Exception as e:
            self.logger.error(f"Erro ao injetar frame FFMPEG: {e}")
            self.stop_pipeline()

    def stop_pipeline(self):
        self.is_running = False
        if self.ffmpeg_proc:
            try:
                self.ffmpeg_proc.stdin.close()
                self.ffmpeg_proc.terminate()
                self.ffmpeg_proc.wait(timeout=3)
            except:
                pass
            self.ffmpeg_proc = None

    def _register_routes(self):
        @self.blueprint.route('/<path:filename>')
        def stream_hls(filename):
            """
            Rotas expostas para o Frontend React consumir. 
            Ex: /api/stream_sota/stream.m3u8 -> Retorna o manifesto M3U8
            Ex: /api/stream_sota/stream0.ts -> Retorna os bytes de h.264
            """
            return send_from_directory(self.hls_dir, filename, 
                                       mimetype="application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/mp2t")
