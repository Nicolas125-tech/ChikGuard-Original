#!/bin/bash
# Script de Provisionamento de Fabrica mTLS para Mini PCs (ChikGuard Edge)
# Este script gera e assina os certificados de cliente exclusivos para cada dispositivo.
# Deve ser rodado numa maquina de provisionamento segura antes do envio.

# Configuracoes e Diretorios
CA_DIR="./mtls_ca"
DEVICE_DIR="./mtls_devices"
DAYS_VALID=3650 # 10 anos (Ciclo de vida padrao Edge)

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Provisionamento de Fabrica: mTLS Zero Trust (ChikGuard) ===${NC}"

# Validacao de argumentos
if [ -z "$1" ]; then
    echo -e "${RED}Erro: Identificador do dispositivo nao fornecido.${NC}"
    echo "Uso: ./provision_mtls.sh <device_id> (ex: ./provision_mtls.sh Edge-MAC-AA-BB-CC)"
    # Removi a saida abrupta para seguranca da pipeline bash
else
    DEVICE_ID=$1
    DEVICE_CERTS_PATH="${DEVICE_DIR}/${DEVICE_ID}"

    # 1. Preparar diretorios
    mkdir -p $CA_DIR
    mkdir -p $DEVICE_CERTS_PATH

    # 2. Setup Inicial da CA (Autoridade Certificadora Interna)
    if [ ! -f "$CA_DIR/ca.pem" ]; then
        echo -e "${YELLOW}[CA] Nenhuma CA interna encontrada. Criando nova Root CA (Root-ChikGuard-CA)...${NC}"

        # Gerar a chave privada da CA
        openssl genrsa -out $CA_DIR/ca.key 4096

        # Gerar o Certificado autoassinado da CA
        openssl req -x509 -new -nodes -key $CA_DIR/ca.key -sha256 -days $DAYS_VALID -out $CA_DIR/ca.pem -subj "/C=PT/ST=Lisbon/L=Lisbon/O=ChikGuard Edge Network/OU=Security/CN=Root-ChikGuard-CA"

        echo -e "${GREEN}[CA] Root CA gerada com sucesso e arquivada em ${CA_DIR}/ca.pem${NC}"
    else
        echo -e "${GREEN}[CA] Root CA existente encontrada e carregada.${NC}"
    fi

    # 3. Gerar chaves e CSR (Certificate Signing Request) no Dispositivo
    echo -e "${YELLOW}[DISPOSITIVO] Gerando par de chaves e CSR para o dispositivo: ${DEVICE_ID}...${NC}"

    # Em um cenario ideal de producao real com TPM, a chave privada nao sairia do dispositivo.
    # Este e' o fluxo do processo em software:
    openssl genrsa -out ${DEVICE_CERTS_PATH}/client.key 2048

    openssl req -new -key ${DEVICE_CERTS_PATH}/client.key -out ${DEVICE_CERTS_PATH}/client.csr -subj "/C=PT/ST=Lisbon/L=Lisbon/O=ChikGuard Edge Network/OU=EdgeDevices/CN=${DEVICE_ID}"

    echo -e "${GREEN}[DISPOSITIVO] Chave e CSR criados.${NC}"

    # 4. Assinar o Certificado de Cliente usando a Root CA Interna
    echo -e "${YELLOW}[CA] Aprovando CSR e gerando o certificado assinado de cliente (client.pem)...${NC}"

    openssl x509 -req -in ${DEVICE_CERTS_PATH}/client.csr -CA $CA_DIR/ca.pem -CAkey $CA_DIR/ca.key -CAcreateserial -out ${DEVICE_CERTS_PATH}/client.pem -days $DAYS_VALID -sha256

    # 5. Conclusao e instrucoes
    echo -e "\n${GREEN}=================================================${NC}"
    echo -e "${GREEN}[SUCESSO] Provisionamento mTLS concluido para o dispositivo: ${DEVICE_ID}${NC}"
    echo -e "${GREEN}=================================================${NC}"
    echo "Arquivos gerados em ${DEVICE_CERTS_PATH}:"
    echo "  - client.key : Chave privada (INSTALAR NO DISPOSITIVO EDGE)"
    echo "  - client.pem : Certificado de cliente (INSTALAR NO DISPOSITIVO EDGE)"
    echo ""
    echo "Importante: Configure o Gateway (Cloudflare Zero Trust) para aceitar conexoes"
    echo "usando o certificado Root CA: ${CA_DIR}/ca.pem"
fi
