<div align="center">

<img src="docs/screenshots/logo.jpeg" alt="ChikGuard Logo" width="120" />

# ChikGuard

![ChikGuard Banner](docs/screenshots/banner.png)

**Poultry monitoring system with computer vision, IoT sensors, and edge computing.**

[![CI](https://github.com/Nicolas125-tech/ChikGuard-Original/actions/workflows/ci.yml/badge.svg)](https://github.com/Nicolas125-tech/ChikGuard-Original/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![React Native](https://img.shields.io/badge/React%20Native-Expo-000020?logo=expo&logoColor=white)](https://expo.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](./docker-compose.yml)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-NoSQL-47A248?logo=mongodb&logoColor=white)](https://mongodb.com)

</div>

## What is ChikGuard?

ChikGuard is a monitoring platform for commercial poultry farms. It uses YOLOv8 for computer vision, WebRTC for video, sensors for temperature, humidity, and ammonia, and an FSM to control actuators.

| Layer | Stack |
|---|---|
| **Backend** | Python 3.12, Flask, Flask-SocketIO, aiortc, SQLAlchemy |
| **Vision AI** | YOLOv8 (ONNX), OpenCV, custom tracking pipeline |
| **Frontend** | React 18, Vite, TailwindCSS, Recharts |
| **Mobile** | React Native (Expo) |
| **Database** | Supabase (PostgreSQL) + MongoDB (NoSQL) + local SQLite fallback |
| **Infra** | Docker Compose, Cloudflare Tunnel, mTLS |

## Features

- Live video streaming via WebRTC with per-camera AI inference
- Bird counting and behavior analysis
- Sensor data collection (temperature, humidity, ammonia, audio)
- Autonomous FSM for actuator control (ventilation, heating)
- ESG compliance reports (PDF generation with ReportLab)
- RBAC and JWT auth with Supabase Auth and OAuth providers
- Mobile app for remote monitoring
- Plugin system for custom AI modules
- Lameness detection (pose estimation) using YOLOv8-Pose and MQTT
- Local execution with Cloudflare Tunnel for remote access

## Architecture

```
ChikGuard/
├── backend/              # Python/Flask API + AI pipeline
│   ├── app.py            # Main entrypoint
│   ├── database.py       # ORM models (SQLAlchemy)
│   ├── src/
│   │   ├── api/          # REST endpoints (auth, sensors, devices, reports, WebRTC)
│   │   ├── core/         # Config, logger, state machine (FSM)
│   │   ├── vision/       # CV inference pipeline
│   │   ├── cv_master/    # Orchestration layer
│   │   ├── agents/       # Autonomous AI agents
│   │   ├── alerts/       # Push notification providers
│   │   ├── audio/        # Acoustic anomaly detection
│   │   ├── mlops/        # Model versioning & management
│   │   ├── reports/      # PDF report generation
│   │   ├── security/     # Auth middleware, hardening, mTLS
│   │   └── plugins/      # Plugin base & manager
│   ├── plugins/          # Pluggable AI modules
│   ├── scripts/          # Utility & pipeline scripts
│   ├── models/           # ML model weights (see models/README.md)
│   └── tests/            # Pytest test suite
├── frontend/             # React + Vite dashboard
├── mobile/               # Expo React Native app
├── docs/                 # Architecture docs & screenshots
├── scripts/              # DevOps & infra scripts
│   └── simulators/       # Data & video simulators
└── supabase/
    └── migrations/       # Database migrations
```

### Polyglot Persistence Architecture

ChikGuard uses multiple databases to handle the computer vision pipeline and sync transactional data with the cloud.

*   **PostgreSQL:** Handled via SQLAlchemy (`src/db/session.py`). Used for RBAC, sensor aggregates (`Reading`), events (`EventLog`), and periodic CV snapshots (`BirdSnapshot`).
*   **MongoDB:** Handled via an async Motor singleton (`src/db/nosql_session.py`). The CV pipeline (`cv_runner.py`) buffers bounding boxes, trajectories, and heatmap coordinates in memory using `MongoDBBatchWriter` and writes them asynchronously to MongoDB (`cv_detections`, `cv_track_points`, `cv_heatmap_coords`).

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ & npm
- Docker & Docker Compose
- A [Supabase](https://supabase.com) project

### 1. Clone and configure

```bash
git clone https://github.com/Nicolas125-tech/ChikGuard-Original.git
cd ChikGuard
cp .env.example .env
# Edit .env with your credentials
```

### 2. Download AI Models

See [`backend/models/README.md`](backend/models/README.md) for instructions to download the YOLOv8 model weights.

### 3. Run with Docker

```bash
docker-compose up --build
```

- **Backend API:** `http://localhost:5000`
- **Frontend:** `http://localhost:5173`

### 4. Run locally (development)

**Backend:**
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python app.py
```

> **Hybrid Mode (USB Camera Development on Windows):** 
> Docker on Windows and Mac cannot easily access physical USB cameras. To use a local webcam (`SIM_VIDEO_PATH=0`), run the databases via Docker and the backend natively via Python:
> ```bash
> # 1. Start Infrastructure
> docker-compose up -d mongo
> 
> # 2. Run Backend natively
> cd backend
> .venv\Scripts\activate
> python main.py
> ```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Mobile:**
```bash
cd mobile
npm install
npm start
```

### 5. Running the Edge Lameness Detection Pipeline

The pipeline calculates the tibiotarsal angle. It triggers an MQTT event if:
- Average angle < 60°
- Angle variance < 5.0

```bash
cd backend
# Install paho-mqtt if not present: pip install paho-mqtt
python scripts/run_lameness_edge.py
```

## Plugin System

ChikGuard supports custom plugins. Each plugin lives in `backend/plugins/<name>/plugin.py`:

```python
from src.plugins.base import PluginBase, PluginInfo

class FireDetectionPlugin(PluginBase):
    info = PluginInfo(name="fire_detection", version="1.0.0", description="Detects fire in video frames")

def register():
    return FireDetectionPlugin()
```

### Biosafety Audit Plugin (Heimdall)
This plugin monitors compliance for Personal Protective Equipment (PPE) and vehicle presence in the `ENTRANCE` and `SANITARY_BARRIER` zones.

* **How it works:**
  - Runs inference using a custom YOLOv8 model (`yolov8n-epi.engine`).
  - Targets restricted entry zones.
  - Matches detected people with required PPE categories like helmets, vests, and boots.
  - Logs `CRITICAL` severity events to the database if a requirement is violated.

* **Configuration:**
  - `BIOSAFETY_MODEL_PATH`: Path to the YOLOv8 weight file.
  - `BIOSAFETY_REQUIRED_EPIS`: List of mandatory items to monitor (e.g., `["helmet", "vest", "boots"]`).

* **Running tests:**
  ```bash
  cd backend
  .venv\Scripts\pytest tests/plugins/
  ```

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/summary` | System summary (CV and sensors) |
| `GET` | `/api/sensors/live` | Live sensor readings |
| `POST` | `/api/auto-mode` | Update FSM automation rules |
| `POST` | `/api/ventilacao` | Turn ventilation on/off |
| `POST` | `/api/aquecedor` | Turn heater on/off |
| `GET` | `/api/estado-dispositivos` | Get current state of devices |
| `GET` | `/api/history` | Historical sensor data |
| `POST` | `/api/webrtc/offer` | WebRTC video stream handshake |
| `POST` | `/api/reports/esg` | Generate ESG compliance PDF |
| `GET` | `/api/accounts/me` | Authenticated user details |

## Screenshots

<details>
<summary><b>Web Dashboard</b></summary>

| Landing | Login | Admin Dashboard |
|---|---|---|
| ![Landing](docs/screenshots/web-landing.jpeg) | ![Login](docs/screenshots/web-login.jpeg) | ![Admin Dashboard](docs/screenshots/admin_dashboard.png) |

| Overview | Birds | History |
|---|---|---|
| ![Overview](docs/screenshots/web-overview.jpeg) | ![Birds](docs/screenshots/web-aves.jpeg) | ![History](docs/screenshots/web-historico.jpeg) |

| Devices | Settings | System |
|---|---|---|
| ![Devices](docs/screenshots/web-dispositivos.jpeg) | ![Settings](docs/screenshots/web-configuracoes.jpeg) | ![System](docs/screenshots/web-sistema.jpeg) |

</details>

<details>
<summary><b>Mobile App</b></summary>

| Login | Monitor | Birds |
|---|---|---|
| ![Login](docs/screenshots/mobile-login.jpeg) | ![Monitor](docs/screenshots/mobile-monitor.jpeg) | ![Birds](docs/screenshots/mobile-aves.jpeg) |

| Alerts | History | Settings |
|---|---|---|
| ![Alerts](docs/screenshots/mobile-alertas.jpeg) | ![History](docs/screenshots/mobile-historico.jpeg) | ![Settings](docs/screenshots/mobile-ajustes.jpeg) |

| System | | |
|---|---|---|
| ![System](docs/screenshots/mobile-sistema.jpeg) | | |

</details>

## Documentation

| Document | Description |
|---|---|
| [Edge Security Architecture](docs/EDGE_SECURITY_ARCHITECTURE.md) | mTLS, Cloudflare Tunnel, edge hardening |
| [IAM and Supabase Proposal](docs/IAM_SUPABASE_PROPOSAL.md) | Identity and access management design |
| [Linux Setup (CV)](docs/LINUX_SETUP_CV.md) | Setting up computer vision on Linux |
| [Windows Setup (CV)](docs/WINDOWS_SETUP_CV.md) | Setting up computer vision on Windows |

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
