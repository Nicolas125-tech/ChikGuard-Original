import os
import subprocess
import logging
import onnxruntime as ort
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class TPMModelLoader:
    """
    Classe responsavel por carregar e decriptar o modelo de IA (ONNX)
    usando a chave de hardware (TPM 2.0).
    """

    def __init__(self, tpm_handle_address: str = "0x81000000"):
        self.tpm_handle_address = tpm_handle_address
        self._key = None

    def _unseal_key_from_tpm(self) -> bytes:
        """
        Interage com o modulo TPM 2.0 via tpm2-tools para extrair a chave.
        No ambiente de desenvolvimento (ou sem TPM), faz o mock para permitir testes.
        """
        # Verifica se estamos em modo DEV (mock)
        if os.environ.get("DEV_MODE") == "true":
            logger.warning("DEV_MODE ativado: Usando chave MOCK para decriptacao do modelo.")
            return b"0123456789abcdef0123456789abcdef" # Chave Mock de 32 bytes (256 bit)

        logger.info(f"Iniciando deselamento da chave do TPM no handle {self.tpm_handle_address}...")
        try:
            # Comando padrao do tpm2-tools para ler dados non-volatile (NV)
            # ou usar tpm2_unseal se a chave foi criada com policy
            cmd = ["tpm2_unseal", "-c", self.tpm_handle_address]

            result = subprocess.run(cmd, capture_output=True, check=True)
            key = result.stdout

            if len(key) not in [16, 24, 32]:
                 raise ValueError("Tamanho de chave invalido extraido do TPM.")

            logger.info("Chave decriptada do TPM com sucesso.")
            return key

        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao acessar o TPM 2.0: {e.stderr.decode('utf-8')}")
            raise RuntimeError("Falha na autenticacao de hardware (TPM). O sistema nao pode inicializar a IA offline.")
        except Exception as e:
            logger.error(f"Erro inesperado no TPM: {e}")
            raise

    def load_encrypted_onnx_model(self, encrypted_file_path: str) -> ort.InferenceSession:
        """
        Le o arquivo .enc do disco, decripta (AES-256-GCM) usando a chave do TPM,
        e carrega os bytes resultantes diretamente na RAM do onnxruntime.
        O modelo original NUNCA e escrito no disco.
        """
        if not os.path.exists(encrypted_file_path):
            raise FileNotFoundError(f"Modelo cifrado nao encontrado em: {encrypted_file_path}")

        # 1. Recuperar chave do hardware
        if not self._key:
            self._key = self._unseal_key_from_tpm()

        logger.info(f"Lendo modelo cifrado de {encrypted_file_path}")

        # 2. Ler os bytes cifrados do disco
        with open(encrypted_file_path, "rb") as f:
            encrypted_data = f.read()

        # O padrao AES-GCM geralmente usa 12 bytes para o IV (Nonce) no inicio do arquivo
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        logger.info("Decriptando o modelo (AES-GCM) diretamente na RAM...")
        try:
             # 3. Decriptacao em RAM
             aesgcm = AESGCM(self._key)
             # plaintext bytes (o binario real do .onnx)
             onnx_bytes = aesgcm.decrypt(iv, ciphertext, None)

             # 4. Carregar o modelo no ONNX Runtime usando exclusivamente a RAM
             logger.info("Carregando modelo ONNX do buffer de memoria...")
             session = ort.InferenceSession(onnx_bytes, providers=['CPUExecutionProvider'])
             logger.info("Modelo ONNX carregado na memoria com sucesso e pronto para inferencia.")

             # Opcional: Para maior seguranca, limpar onnx_bytes da RAM apos carregar,
             # porem o garbage collector do Python fara isso eventualmente.
             del onnx_bytes

             return session

        except Exception as e:
             logger.error("Falha ao decriptar ou carregar o modelo ONNX. Chave incorreta ou arquivo corrompido.")
             raise ValueError("Corrupcao ou violacao de seguranca detectada no modelo de IA.") from e
