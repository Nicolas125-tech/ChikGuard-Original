import numpy as np

try:
    import librosa
except ImportError:
    librosa = None
    import logging
    logging.warning("A biblioteca 'librosa' nao esta instalada. Algumas funcoes de audio estarao indisponiveis.")


def compute_mel_spectrogram(
    audio_buffer: np.ndarray,
    sr: int = 16000,
    n_mels: int = 64,
    n_fft: int = 1024,
    hop_length: int = 512
) -> np.ndarray:
    """
    Pré-processa um buffer de áudio PCM (WAV) e gera um Espectrograma Mel logarítmico,
    pronto para inferência em redes neurais leves (ex: YAMNet).
    
    A taxa de amostragem (sr) recomendada para captura na borda e modelos de 
    classificação acústica (AudioSet) é de 16.000 Hz (16kHz) mono. Isso reduz a 
    banda necessária na edge e é padrão para inferência de voz e ruídos avícolas.
    
    Args:
        audio_buffer: Numpy array 1D contendo a forma de onda do áudio (raw PCM).
        sr: Sample rate do áudio.
        n_mels: Número de bandas de frequência Mel (features extraídas).
        n_fft: Tamanho da janela da FFT (Fast Fourier Transform).
        hop_length: Salto (step) entre os frames, define a resolução temporal.
        
    Returns:
        Um tensor Numpy 2D (espectrograma) normalizado. Retorna um array vazio 
        se a biblioteca base não estiver instalada (fallback).
    """
    if librosa is None:
        # Fallback de seguranca caso o deploy na edge nao tenha librosa
        return np.zeros((n_mels, int(len(audio_buffer)/hop_length)))

    # Converter para float32 e evitar divisao por zero
    y = audio_buffer.astype(np.float32)
    max_val = np.max(np.abs(y))
    if max_val > 0:
        y = y / max_val
        
    # Extrair Espectrograma Mel
    mel_spec = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels
    )
    
    # Converter a amplitude para escala em decibéis (log)
    log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Normalização z-score padronizada (opcional dependendo do modelo)
    # mean = np.mean(log_mel_spec)
    # std = np.std(log_mel_spec) + 1e-6
    # normalized_spec = (log_mel_spec - mean) / std
        
    return log_mel_spec
