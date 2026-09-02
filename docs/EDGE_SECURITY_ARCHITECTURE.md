# ChikGuard: Especificação Técnica de Segurança Edge

Este documento descreve a arquitetura de segurança para os dispositivos Edge (Mini PCs) do ChikGuard em ambientes rurais e a sua integração com a Cloud. O foco é a proteção de Propriedade Intelectual (Modelos de IA e Código Fonte) e a garantia de Zero Trust via mTLS.

## 1. Segurança no Edge (Proteção Física e IP)

### 1.1 Proteção do Modelo de IA (YOLOv8 para ONNX)
O modelo de Inteligência Artificial opera em ambientes sem garantia de internet e está sujeito a roubo ou clonagem de disco. A proteção baseia-se em **Hardware Root of Trust (TPM 2.0)**.

*   **Estado de Repouso (Disco):** O modelo é armazenado cifrado (`.enc`) usando criptografia simétrica (AES-256-GCM). O modelo original (`.onnx`) não é gravado no disco do dispositivo em produção.
*   **Gestão da Chave (TPM 2.0):** Durante o provisionamento na fábrica, uma chave simétrica de 256 bits é gerada e selada (sealed) no chip TPM 2.0 da motherboard do Mini PC. O TPM vincula esta chave aos registos de configuração da plataforma (PCRs), como o Secure Boot e o firmware da BIOS. Se o SSD for removido e montado noutro computador, os PCRs não coincidem e o TPM não liberta a chave.
*   **Decriptação em Memória (RAM):** No arranque do sistema, a aplicação Python invoca o TPM para deselar a chave. O ficheiro `.enc` é lido do disco, decriptado usando a chave em memória, e o payload de bytes (o modelo ONNX) é carregado na RAM utilizando a API do `onnxruntime` (`InferenceSession(bytes)`). A chave e o modelo em plain-text residem apenas na memória volátil.

### 1.2 Prevenção de Engenharia Reversa (Ofuscação)
Para proteger os algoritmos de automação e regras de negócio no backend Python, o código fonte não é distribuído em `.py` nem em bytecode `.pyc`.

*   **Compilação Nativa (Cython):** Os ficheiros da aplicação (como `backend/app.py`, `backend/src/core/state_machine.py`) são compilados usando **Cython** durante o pipeline de CI/CD (GitHub Actions).
*   **Artefatos de Deploy:** O Cython traduz o código Python para C e um compilador (como o GCC) gera bibliotecas partilhadas nativas (`.so` em Linux ou `.pyd` em Windows). O pacote enviado para o dispositivo Edge contém apenas os ficheiros `.so`.
*   **Benefícios:** Esta abordagem impede a engenharia reversa do código fonte e reduz o uso de recursos em ambientes Edge.

## 2. Zero Trust e Comunicação (mTLS)

### 2.1 Autenticação Criptográfica de Clientes
A comunicação entre o Mini PC (Edge) e a API na Cloud não depende apenas de tokens (JWT), que podem ser roubados e reutilizados. A arquitetura exige Autenticação Mútua (mTLS).

*   **Terminação no Gateway:** A terminação TLS e a verificação do certificado de cliente ocorrem no Gateway (ex: Cloudflare Zero Trust ou Cloudflare Tunnels). O servidor Flask backend confia nas requisições validadas e reencaminhadas pelo túnel.
*   **Infraestrutura de Chaves Públicas (PKI) Interna:** Para a emissão dos certificados, é utilizada uma CA (Autoridade Certificadora) Interna gerida num ambiente seguro.
*   **Provisionamento de Fábrica:** Antes do envio do dispositivo para o cliente, um script automatizado corre no Mini PC e na máquina de provisionamento. O script gera um par de chaves local no dispositivo, cria uma solicitação de assinatura de certificado (CSR), envia para a CA local, assina-o e instala o certificado de cliente resultante (`client.pem`). Cada Mini PC recebe um certificado exclusivo, revogável individualmente no gateway da Cloud em caso de comprometimento.
