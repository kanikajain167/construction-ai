# Multimodal Construction Intelligence Platform

Skill Wallet Capstone Project 1. A Streamlit decision-support app that analyses construction site photos for PPE safety compliance and concrete cracks, estimates project cost and real estate value in INR, and gives weather-aware daily site protocols.

## Features

| Tab | What it does |
|-----|--------------|
| Safety and PPE audit | Upload a site photo. Returns a safety score (0-100), overall status, a PPE checklist (helmet, high-vis vest, steel-toe boots, harness), and hazards with severity (Low to Critical) and remedies. Downloadable JSON report. |
| Crack diagnostics | Upload a concrete or wall photo. Classifies the defect (Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling) with estimated width in mm, severity score, root causes, repairs and urgency. |
| Planning and valuation | Inputs: structure type, built-up area, location tier, completion %. Outputs: total budget, capex incurred, current asset value (Lakhs/Crores), steel and cement needs, milestone progress, and a conceptual 3D rendering via Pollinations (Flux). |
| Site assistant | Weather selector (High Wind, Heavy Rain, Extreme Heat, Normal) with safety alerts, plus a multi-turn engineering chatbot. |

## Tech stack

Python 3.9+, Streamlit, Google Gemini (multimodal), Pillow, Pollinations/Flux API, JSON data contracts. No database.

## Run locally

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501.

## API key

Paste a Google Gemini API key (free at https://aistudio.google.com) into the sidebar for live image analysis and chatbot answers.

Without a key the app runs in **demonstration mode**: the safety and crack tabs return sample results (not based on the uploaded image) and the chatbot uses a small built-in knowledge base. Planning, valuation, weather alerts and rendering work in both modes.

## JSON data contracts

Safety audit:

```json
{"safety_score": 0, "overall_status": "", "ppe_detection": {"helmet": {"detected": true, "note": ""}},
 "hazards": [{"hazard": "", "severity": "Low|Medium|High|Critical", "remedy": ""}], "summary": ""}
```

Crack diagnosis:

```json
{"defect_type": "", "estimated_width_mm": 0, "severity_score": 0, "severity": "", "root_causes": [],
 "recommended_repairs": [], "urgency": "", "notes": ""}
```

## Deployment

Deployed on Streamlit Community Cloud: connect this repo, branch `main`, main file `app.py`.

## Known limitations

- Cost, market-value, steel and cement rates are indicative planning assumptions, not quotations. Verify with local contractors and registered valuers.
- AI output can be wrong. Safety and structural findings must be confirmed by a qualified engineer or safety officer.
- Demonstration mode output is sample data, not an analysis of the uploaded image.
- Gemini model names change over time; pick an available model in the sidebar if one fails.
