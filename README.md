# pi-mono Orchestrator — Quick Start

## 1) Prereqs
- NVIDIA GPU + recent CUDA drivers
- Docker + Compose (or run services natively)
- Models downloaded into `/models` (mount into containers)

## 2) Configure
- Edit `policy/orchestrator_policy.yaml` if needed.
- Optional: set env files in `docker/`.

## 3) Start services
```bash
cd docker
docker compose up -d

Run the following locally in Shell:
pip install -r orchestrator/requirements.txt
python orchestrator/router_skeleton.py

And to use Weasyprint (for Reports as PDFs):
pip install markdown weasyprint
python orchestrator/publish_report.py notes.md -o notes.pdf --title "Daily Build Report" --footer "© pi-mono"

