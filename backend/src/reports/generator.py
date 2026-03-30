import os
import smtplib
from email.message import EmailMessage
from datetime import timedelta
from database import Reading, SensorReading, EventLog, AcousticReading

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None
    A4 = None

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")

def _send_report_email(file_path, recipient):
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    sender = os.getenv("SMTP_FROM", smtp_user).strip()

    if not smtp_host or not sender or not recipient:
        return False, "smtp_not_configured"

    msg = EmailMessage()
    msg["Subject"] = "ChikGuard - Relatorio semanal"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content("Segue o relatorio semanal do ChikGuard em anexo.")

    with open(file_path, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=os.path.basename(file_path))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)

def generate_weekly_report(app_context, camera_id, utcnow_func, week_end=None):
    if canvas is None or A4 is None:
        raise RuntimeError("reportlab nao instalado. Instale reportlab no backend.")

    if week_end is None:
        week_end = utcnow_func()
    week_start = week_end - timedelta(days=7)

    with app_context():
        readings = Reading.query.filter(Reading.timestamp >= week_start, Reading.timestamp <= week_end).all()
        sensors = SensorReading.query.filter(
            SensorReading.camera_id == camera_id,
            SensorReading.timestamp >= week_start,
            SensorReading.timestamp <= week_end,
        ).all()
        events = EventLog.query.filter(
            EventLog.camera_id == camera_id,
            EventLog.timestamp >= week_start,
            EventLog.timestamp <= week_end,
        ).all()

    temps = [r.temperatura for r in readings]
    temp_min = min(temps) if temps else None
    temp_max = max(temps) if temps else None
    temp_avg = (sum(temps) / len(temps)) if temps else None

    amms = [s.ammonia_ppm for s in sensors if s.ammonia_ppm is not None]
    hums = [s.humidity_pct for s in sensors if s.humidity_pct is not None]
    feed = [s.feed_level_pct for s in sensors if s.feed_level_pct is not None]
    water = [s.water_level_pct for s in sensors if s.water_level_pct is not None]

    fname = f"weekly_report_{camera_id}_{week_end.strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(REPORTS_DIR, fname)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, f"ChikGuard - Relatorio semanal ({camera_id})")
    y -= 26
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Periodo: {week_start.strftime('%Y-%m-%d')} ate {week_end.strftime('%Y-%m-%d')}")
    y -= 20

    lines = [
        f"Temperatura minima: {temp_min:.1f} C" if temp_min is not None else "Temperatura minima: sem dados",
        f"Temperatura maxima: {temp_max:.1f} C" if temp_max is not None else "Temperatura maxima: sem dados",
        f"Temperatura media: {temp_avg:.1f} C" if temp_avg is not None else "Temperatura media: sem dados",
        f"Alertas/eventos: {len(events)}",
        f"Umidade media: {sum(hums)/len(hums):.1f}%" if hums else "Umidade media: sem dados",
        f"Amonia media: {sum(amms)/len(amms):.1f} ppm" if amms else "Amonia media: sem dados",
        f"Racao media restante: {sum(feed)/len(feed):.1f}%" if feed else "Racao media restante: sem dados",
        f"Agua media restante: {sum(water)/len(water):.1f}%" if water else "Agua media restante: sem dados",
    ]
    for line in lines:
        c.drawString(40, y, line)
        y -= 16

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Eventos recentes")
    y -= 18
    c.setFont("Helvetica", 9)
    for ev in sorted(events, key=lambda e: e.timestamp, reverse=True)[:20]:
        msg = f"{ev.timestamp.strftime('%Y-%m-%d %H:%M:%S')} [{ev.level}] {ev.event_type} - {ev.message}"
        c.drawString(40, y, msg[:110])
        y -= 13
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

    c.save()
    return path


def generate_esg_report(app_context, camera_id, utcnow_func, days=30):
    if canvas is None or A4 is None:
        raise RuntimeError("reportlab nao instalado. Instale reportlab no backend.")

    days = max(7, min(int(days), 120))
    end_dt = utcnow_func()
    start_dt = end_dt - timedelta(days=days)

    with app_context():
        readings = Reading.query.filter(Reading.timestamp >= start_dt, Reading.timestamp <= end_dt).all()
        acoustic_rows = AcousticReading.query.filter(
            AcousticReading.camera_id == camera_id,
            AcousticReading.timestamp >= start_dt,
            AcousticReading.timestamp <= end_dt,
        ).all()
        events = EventLog.query.filter(
            EventLog.camera_id == camera_id,
            EventLog.timestamp >= start_dt,
            EventLog.timestamp <= end_dt,
        ).all()

    total = len(readings)
    normal = len([r for r in readings if r.status == "NORMAL"])
    calor = len([r for r in readings if r.status == "CALOR"])
    frio = len([r for r in readings if r.status == "FRIO"])
    low_stress_pct = (normal / total * 100.0) if total else 0.0
    thermal_stress_pct = (100.0 - low_stress_pct) if total else 0.0
    avg_resp = (
        sum(float(a.respiratory_health_index) for a in acoustic_rows) / len(acoustic_rows)
        if acoustic_rows
        else 100.0
    )
    critical_events = len([e for e in events if str(e.level).lower() == "high"])
    esg_score = max(0.0, min(100.0, (low_stress_pct * 0.55) + (avg_resp * 0.35) - (critical_events * 0.8)))
    market_flag = "APTO para mercados exigentes (Europa/Japao)" if esg_score >= 80 else "Necessita melhorias para mercados premium"

    fname = f"esg_report_{camera_id}_{end_dt.strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(REPORTS_DIR, fname)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, f"ChikGuard - Relatorio ESG ({camera_id})")
    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Periodo analisado: {start_dt.strftime('%Y-%m-%d')} ate {end_dt.strftime('%Y-%m-%d')}")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Indicadores de Sustentabilidade e Bem-Estar")
    y -= 18
    c.setFont("Helvetica", 10)
    lines = [
        f"Leituras termicas totais: {total}",
        f"Baixo stress termico (status NORMAL): {low_stress_pct:.1f}%",
        f"Stress termico (CALOR+FRIO): {thermal_stress_pct:.1f}%",
        f"Ocorrencias CALOR: {calor} | FRIO: {frio}",
        f"Saude respiratoria media (acustica): {avg_resp:.1f}/100",
        f"Eventos criticos de operacao: {critical_events}",
        f"ESG Score consolidado: {esg_score:.1f}/100",
        f"Status exportacao: {market_flag}",
    ]
    for line in lines:
        c.drawString(40, y, line)
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Conclusao automatica")
    y -= 16
    c.setFont("Helvetica", 10)
    conclusion = (
        "As aves apresentaram baixo stress termico e estabilidade ambiental, "
        "favorecendo conformidade ESG e valor agregado para exportacao."
        if esg_score >= 80
        else
        "Foram detectadas variacoes relevantes de conforto termico. Recomenda-se "
        "otimizar ventilacao, setpoint termico e rotina de monitoramento."
    )
    c.drawString(40, y, conclusion[:120])
    y -= 14
    if len(conclusion) > 120:
        c.drawString(40, y, conclusion[120:240])

    c.save()
    return path