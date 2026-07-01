import os

import requests
from flask import Blueprint, jsonify, request

from src.security.auth import require_auth


def _retrieve_knowledge_base(query: str) -> str:
    """Função leve de RAG para recuperar seções do manual de manejo baseado na dúvida do produtor."""
    try:
        # Tenta carregar o arquivo a partir da raiz do backend ou local relativo
        handbook_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "../../../backend/data/handling_handbook.txt"
            )
        )
        if not os.path.exists(handbook_path):
            handbook_path = "data/handling_handbook.txt"
            if not os.path.exists(handbook_path):
                return ""

        with open(handbook_path, "r", encoding="utf-8") as f:
            text = f.read()

        sections = text.split("\n\n")
        relevant = []
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if not keywords:
            return ""

        for section in sections:
            score = sum(1 for kw in keywords if kw in section.lower())
            if score > 0:
                relevant.append((score, section))

        relevant.sort(key=lambda x: x[0], reverse=True)
        return "\n\n".join([sec[1] for sec in relevant[:2]])
    except Exception:
        return ""


def create_agents_blueprint(api_deps):
    bp = Blueprint("agents_api", __name__, url_prefix="/api/agents")
    SensorReading = api_deps["SensorReading"]
    AcousticReading = api_deps["AcousticReading"]

    # Imports locais de tabelas adicionais para evitar dependências circulares
    from database import Batch, EventLog
    from src.security.rate_limiter import limiter

    @bp.route("/chat", methods=["POST"])
    @require_auth()
    @limiter.limit("10 per minute")
    def chat():
        """Endpoint de chat conversacional com o co-piloto do ChikGuard usando a API do Gemini."""
        data = request.json or {}
        user_message = data.get("message", "")
        if not user_message:
            return jsonify({"error": "Mensagem vazia"}), 400
        if len(str(user_message)) > 2000:
            return (
                jsonify(
                    {"error": "Tamanho da mensagem excede o limite (2000 caracteres)"}
                ),
                400,
            )

        # Obtém a chave da API do Gemini a partir do ambiente (.env)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify(
                {
                    "response": "Olá! Sou o assistente de IA do ChikGuard. No momento, a chave da API do Gemini não está configurada no servidor (variável `GEMINI_API_KEY`), então não consigo responder usando inteligência artificial avançada na nuvem. Contudo, todos os sensores locais e algoritmos de visão continuam protegendo o galpão perfeitamente."
                }
            )

        # 1. Coleta dados de sensores recentes
        last_sensor = SensorReading.query.order_by(
            SensorReading.timestamp.desc()
        ).first()
        sensor_text = "Sem leituras de sensores recentes nas últimas horas."
        if last_sensor:
            sensor_text = (
                f"Temperatura: {last_sensor.temperature_c:.1f}°C, "
                f"Umidade: {last_sensor.humidity_pct:.1f}%, "
                f"Amônia: {last_sensor.ammonia_ppm:.1f} ppm, "
                f"Nível de Ração: {last_sensor.feed_level_pct:.1f}%, "
                f"Nível de Água: {last_sensor.water_level_pct:.1f}%"
            )

        # 2. Coleta dados acústicos recentes
        last_acoustic = AcousticReading.query.order_by(
            AcousticReading.timestamp.desc()
        ).first()
        acoustic_text = "Sem dados de áudio recentes."
        if last_acoustic:
            acoustic_text = (
                f"Saúde Respiratória: {last_acoustic.respiratory_health_index:.2f} (ideal é 1.0), "
                f"Índice de Tosse: {last_acoustic.cough_index:.2f} (ideal é 0.0), "
                f"Estresse Sonoro: {last_acoustic.stress_audio_index:.2f}"
            )

        # 3. Coleta dados do lote ativo
        active_batch = Batch.query.filter(Batch.active).first()
        batch_text = "Nenhum lote ativo registrado."
        if active_batch:
            batch_text = f"Lote Ativo: {active_batch.name} (Iniciado em: {
                active_batch.start_date.strftime('%d/%m/%Y')
            })"

        # 4. Coleta os alertas e logs de visão mais recentes
        recent_events = (
            EventLog.query.order_by(EventLog.timestamp.desc()).limit(5).all()
        )
        events_text = "Nenhum alerta ou evento recente cadastrado."
        if recent_events:
            events_text = "\n".join(
                [
                    f"[{e.timestamp.strftime('%H:%M:%S')}] {e.event_type} ({e.level}): {e.message}"
                    for e in recent_events
                ]
            )

        # 5. Obtém status dos atuadores
        estado_dispositivos = api_deps.get("estado_dispositivos", {})
        fan_status = "LIGADA" if estado_dispositivos.get("ventilacao") else "DESLIGADA"
        heater_status = (
            "LIGADO" if estado_dispositivos.get("aquecedor") else "DESLIGADO"
        )
        devices_text = (
            f"Ventilação (Exaustores): {fan_status}, Aquecedor: {heater_status}"
        )

        # 6. Recupera contexto do manual de manejo (RAG local)
        kb_context = _retrieve_knowledge_base(user_message)
        kb_text = (
            f"- Diretrizes do Manual de Manejo Relevantes:\n{kb_context}\n\n"
            if kb_context
            else ""
        )

        # Criação do prompt do sistema embutido com contexto em tempo real do galpão e RAG
        system_prompt = (
            "Você é o Co-Piloto IA do ChikGuard, um especialista virtual em avicultura de precisão.\n"
            "Seu dever é responder a perguntas do produtor sobre o estado do aviário de forma concisa, "
            "clara e profissional, fornecendo insights agronômicos e práticos se detectar problemas.\n\n"
            "ESTADO ATUAL DO AVIÁRIO:\n"
            f"- Lote: {batch_text}\n"
            f"- Telemetria de Sensores: {sensor_text}\n"
            f"- Saúde por Áudio (Acoustics): {acoustic_text}\n"
            f"- Status dos Equipamentos: {devices_text}\n"
            f"- Alertas e Histórico Recente de Visão/Eventos:\n{events_text}\n\n"
            f"{kb_text}"
            "DIRETRIZES DE RESPOSTA:\n"
            "1. Responda em Português do Brasil.\n"
            "2. Utilize os dados de telemetria fornecidos para basear e enriquecer as suas respostas.\n"
            "3. Se houver qualquer leitura de alerta ativo (como amônia > 20ppm, tosse > 0.5 ou carcaça de aves detectadas), "
            "comunique isso claramente ao produtor e sugira a ação preventiva adequada imediatamente."
        )

        # Faz requisição direta para a API REST do Gemini 2.5 Flash
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Instruções do Sistema:\n{system_prompt}\n\nPergunta do Produtor: {user_message}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,  # Baixa temperatura para manter respostas determinísticas e precisas nos dados
                "maxOutputTokens": 800,
            },
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code != 200:
                return (
                    jsonify(
                        {
                            "error": f"Erro na API do Gemini (Código {res.status_code}): {res.text}"
                        }
                    ),
                    500,
                )

            res_data = res.json()
            candidate = res_data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [{}])
            reply = parts[0].get(
                "text",
                "Desculpe, não obtive uma resposta válida da inteligência artificial.",
            )

            return jsonify({"response": reply})
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                "Erro na requisição externa de IA: %s", str(e)
            )
            return jsonify({"error": "Falha interna na requisição de IA"}), 500

    return bp
