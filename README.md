# ArchDesign Agent

Web-app agent for architecture / interior design: site & zoning check -> massing -> 3D / rendering -> drawings & BOQ.
**Round 1 (this release): Phase 1 foundation** - FastAPI + Claude agent loop, zoning/setback calculation (Shapely),
rule sources (agent web research by country, uploaded md/txt/pdf for law & feng shui, editable JSON config).

## Run
```bash
cp .env.example .env            # put your ANTHROPIC_API_KEY
docker compose up --build       # CPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build   # NVIDIA GPU (needs NVIDIA Container Toolkit)
```
Open http://localhost:8000. Local test without Docker: `pip install -r backend/requirements.txt && pytest tests`.

## Rule sources (priority)
1. Documents uploaded in the UI (`data/knowledge/{law,fengshui,other}`)
2. Agent web research for the selected country
3. `config/zoning/<CC>.json` - **TH values are placeholders; verify before use**

## Roadmap
- R2: OR-Tools layout + Trimesh massing - R3: FreeCAD parametric - R4: Blender render, style prompts (Option A), moodboard input, ComfyUI hook (later)
- R5: TechDraw drawings, BOQ (.xlsx), PDF deck

Preliminary tool only - not a substitute for a licensed architect or the local authority.
