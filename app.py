"""Multimodal Construction Intelligence Platform - Skill Wallet Capstone Project 1.
Run: streamlit run app.py
"""
import json
import re
import urllib.parse

import streamlit as st
from PIL import Image

try:
    import google.generativeai as genai
except ImportError:  # app still runs in demo mode
    genai = None

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

# ---------------------------------------------------------------- styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600&display=swap');
:root{--ink:#1d2430;--slab:#e9eaec;--hazard:#f2b705;--blue:#1f4e79;--ok:#1e7f4f;--warn:#c77700;--bad:#b3261e;}
html,body,[class*="css"]{font-family:'Barlow',sans-serif;}
h1,h2,h3{font-family:'Barlow Condensed',sans-serif;letter-spacing:.01em;}
.hero{background:var(--ink);color:#fff;padding:1.4rem 1.6rem;border-radius:6px;margin-bottom:1rem;
 border-bottom:8px solid transparent;border-image:repeating-linear-gradient(135deg,var(--hazard) 0 14px,var(--ink) 14px 28px) 8;}
.hero h1{color:#fff;margin:0;font-size:2.2rem}.hero p{margin:.3rem 0 0;color:#c9ced6}
.metric{background:#fff;border:1px solid #d5d8dd;border-left:6px solid var(--blue);border-radius:4px;padding:.8rem 1rem;}
.metric .l{font-size:.85rem;color:#5b6472}.metric .v{font-family:'Barlow Condensed';font-size:1.9rem;font-weight:700;color:var(--ink)}
.pill{display:inline-block;padding:.15rem .7rem;border-radius:99px;font-weight:600;font-size:.85rem;color:#fff}
.Low,.PASS,.Compliant{background:var(--ok)}.Medium,.Minor{background:var(--warn)}
.High,.Moderate,.Non-Compliant{background:#d9480f}.Critical,.Severe,.FAIL{background:var(--bad)}
.alert{border-left:6px solid var(--hazard);background:#fff8dc;padding:.7rem 1rem;border-radius:4px;margin:.4rem 0;color:var(--ink)}
</style>""", unsafe_allow_html=True)


def metric(label, value):
    st.markdown(f'<div class="metric"><div class="l">{label}</div><div class="v">{value}</div></div>',
                unsafe_allow_html=True)


def pill(text):
    cls = str(text).replace(" ", "-")
    return f'<span class="pill {cls}">{text}</span>'


# ---------------------------------------------------------------- AI helpers
def get_model():
    key = st.session_state.get("api_key", "").strip()
    if not key or genai is None:
        return None
    genai.configure(api_key=key)
    return genai.GenerativeModel(st.session_state.get("model_name", "gemini-1.5-flash"))


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


def analyze_image(prompt, image, demo):
    """Return (data, mode). Falls back to demo data on any failure."""
    model = get_model()
    if model is None:
        return demo, "demo"
    try:
        resp = model.generate_content([prompt, image])
        return parse_json(resp.text), "live"
    except Exception as exc:  # network, quota, bad JSON ...
        st.warning(f"Live analysis failed ({type(exc).__name__}); showing demonstration output. {exc}")
        return demo, "demo"


SAFETY_PROMPT = """You are a certified construction safety officer (OSHA 1926, IS 456, IS 3764).
Audit the worker PPE and hazards in this site photo. Respond with ONLY valid JSON:
{"safety_score":0-100,"overall_status":"Compliant|Needs Improvement|Non-Compliant",
"ppe_detection":{"helmet":{"detected":bool,"note":str},"high_vis_vest":{...},"steel_toe_boots":{...},"safety_harness":{...}},
"hazards":[{"hazard":str,"severity":"Low|Medium|High|Critical","remedy":str}],
"summary":str}"""

CRACK_PROMPT = """You are a structural engineer (IS 456, IS 13935). Classify the defect in this concrete/wall photo.
Respond with ONLY valid JSON:
{"defect_type":"Hairline|Settlement|Structural Shear|Thermal Expansion|Spalling",
"estimated_width_mm":number,"severity_score":0-100,"severity":"Minor|Moderate|Severe",
"root_causes":[str],"recommended_repairs":[str],"urgency":"Routine|Within 30 days|Within 7 days|Immediate","notes":str}"""

DEMO_SAFETY = {
    "safety_score": 62, "overall_status": "Needs Improvement",
    "ppe_detection": {
        "helmet": {"detected": True, "note": "Worn correctly by 2 of 3 workers"},
        "high_vis_vest": {"detected": True, "note": "Visible, one worker without"},
        "steel_toe_boots": {"detected": False, "note": "Canvas shoes observed"},
        "safety_harness": {"detected": False, "note": "No harness at elevated edge"}},
    "hazards": [
        {"hazard": "Unprotected slab edge", "severity": "Critical", "remedy": "Install guardrails and enforce harness tie-off above 1.8 m."},
        {"hazard": "Loose material stacking", "severity": "Medium", "remedy": "Stack within marked zones, keep walkways clear."},
        {"hazard": "Exposed rebar ends", "severity": "High", "remedy": "Fit rebar safety caps."}],
    "summary": "DEMONSTRATION OUTPUT: add a Gemini API key for a real analysis of your photo."}

DEMO_CRACK = {
    "defect_type": "Settlement", "estimated_width_mm": 3.2, "severity_score": 58, "severity": "Moderate",
    "root_causes": ["Differential foundation settlement", "Poor soil compaction", "Water ingress at footing"],
    "recommended_repairs": ["Epoxy injection for cracks above 0.3 mm", "Structural re-grouting", "Crack-gauge monitoring for 3 months"],
    "urgency": "Within 30 days",
    "notes": "DEMONSTRATION OUTPUT: add a Gemini API key for a real analysis of your photo."}

# ---------------------------------------------------------------- cost model (INR)
COST_PER_SQFT = {"Residential RCC": 2200, "Commercial RCC": 2800, "Industrial Steel Shed": 1800, "Villa (Premium)": 3500}
TIER_MULT = {"Tier 1 (Mumbai, Delhi, Bengaluru)": 1.35, "Tier 2 (Pune, Jaipur, Indore)": 1.0, "Tier 3 (Jabalpur, Bhopal-outskirts, others)": 0.82}
MARKET_PER_SQFT = {"Tier 1 (Mumbai, Delhi, Bengaluru)": 9500, "Tier 2 (Pune, Jaipur, Indore)": 5200, "Tier 3 (Jabalpur, Bhopal-outskirts, others)": 3200}
STEEL_KG_SQFT = {"Residential RCC": 4.0, "Commercial RCC": 5.0, "Industrial Steel Shed": 9.0, "Villa (Premium)": 4.5}
CEMENT_BAGS_SQFT = 0.4
MILESTONES = [(0, "Site prep"), (15, "Foundation"), (35, "Superstructure"), (60, "Masonry & MEP"), (80, "Finishing"), (100, "Handover")]


def inr(v):
    return f"₹{v/1e7:.2f} Cr" if v >= 1e7 else f"₹{v/1e5:.2f} Lakhs"


# ---------------------------------------------------------------- weather
WEATHER = {
    "High Wind": ["Suspend all crane and hoist operations above 36 km/h wind.", "Secure scaffolding sheets, loose formwork and materials.", "Restrict work at height; no one on open edges."],
    "Heavy Rain": ["Isolate temporary electrical panels; use RCCB-protected, waterproof connections.", "Stop concrete pouring; cover fresh concrete with tarpaulin.", "Pump out excavations and check slope stability before re-entry."],
    "Extreme Heat": ["Shift heavy work to early morning; enforce hydration breaks every 45 min.", "Cure concrete: wet burlap and spray for at least 7 days, pour in cooler hours.", "Watch for heat-stress symptoms; provide shaded rest areas."],
    "Normal": ["Standard operations permitted; hold the daily toolbox talk.", "Carry out routine PPE and scaffold inspection.", "Log curing records for pours in the last 7 days."]}

KB = {
    "curing": "Cure OPC concrete for at least 7 days (14 for blended cement) per IS 456 Cl. 13.5; keep surfaces continuously moist.",
    "cement": "Typical residential RCC needs about 0.4 bags of cement per sq ft built-up area.",
    "steel": "Residential RCC uses roughly 4 kg of TMT steel per sq ft (Fe500D is common).",
    "crack": "Cracks under 0.3 mm are usually cosmetic; wider or growing cracks need an engineer's assessment, often with epoxy injection.",
    "slump": "Slump of 75-100 mm suits most RCC beams and slabs; check IS 456 Table 7.",
    "ppe": "Minimum PPE: helmet, high-vis vest, steel-toe boots, gloves, and harness above 1.8 m.",
    "cover": "Nominal cover to reinforcement is 20-50 mm depending on exposure (IS 456 Table 16)."}


def chat_reply(history, question):
    model = get_model()
    if model is not None:
        try:
            ctx = "\n".join(f"{m['role']}: {m['content']}" for m in history[-8:])
            p = ("You are a concise senior site engineer in India. Cite IS codes when useful. "
                 f"Conversation:\n{ctx}\nuser: {question}\nassistant:")
            return model.generate_content(p).text
        except Exception as exc:
            return f"Live assistant unavailable ({type(exc).__name__}). Try again or clear the API key."
    hits = [v for k, v in KB.items() if k in question.lower()]
    return " ".join(hits) if hits else "Demo mode knows: curing, cement, steel, cracks, slump, PPE, cover. Add a Gemini key for full answers."


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Setup")
    st.session_state["api_key"] = st.text_input("Google Gemini API key", type="password",
                                                help="Leave empty to use demonstration mode.")
    st.session_state["model_name"] = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])
    if get_model():
        st.success("Live mode")
    else:
        st.info("Demonstration mode: sample outputs, no API calls.")
    st.header("Architecture")
    st.markdown("Streamlit UI → prompt builders → Gemini multimodal → JSON data contract → metric cards and downloadable reports. "
                "No database; state lives in the session.")
    st.header("Features")
    st.markdown("- Safety and PPE audit\n- Crack diagnostics\n- Planning and valuation\n- Weather advisory and site chatbot")

st.markdown('<div class="hero"><h1>Multimodal Construction Intelligence Platform</h1>'
            '<p>Site photos in, safety, structural and cost decisions out.</p></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Safety and PPE audit", "Crack diagnostics", "Planning and valuation", "Site assistant"])

# ---------------------------------------------------------------- tab 1
with tab1:
    up = st.file_uploader("Upload a site photo", type=["jpg", "jpeg", "png"], key="safety_upload")
    if up:
        try:
            img = Image.open(up).convert("RGB")
        except Exception:
            st.error("That file could not be read as an image. Upload a JPG or PNG.")
            st.stop()
        c1, c2 = st.columns([1, 1.3])
        c1.image(img, use_container_width=True)
        if c2.button("Run safety audit", type="primary"):
            with st.spinner("Auditing site..."):
                st.session_state["safety"], st.session_state["safety_mode"] = analyze_image(SAFETY_PROMPT, img, DEMO_SAFETY)
        d = st.session_state.get("safety")
        if d:
            try:
                with c2:
                    m1, m2 = st.columns(2)
                    with m1: metric("Safety score", f"{d['safety_score']}/100")
                    with m2: metric("Hazards found", len(d["hazards"]))
                    st.markdown(f"**Status:** {pill(d['overall_status'])} &nbsp; ({st.session_state['safety_mode']} mode)", unsafe_allow_html=True)
                    st.progress(int(d["safety_score"]) / 100)
                    st.write(d.get("summary", ""))
                st.subheader("PPE checklist")
                cols = st.columns(4)
                for col, (k, v) in zip(cols, d["ppe_detection"].items()):
                    col.markdown(f"**{k.replace('_', ' ').title()}**<br>{pill('PASS' if v['detected'] else 'FAIL')}<br><small>{v.get('note','')}</small>",
                                 unsafe_allow_html=True)
                st.subheader("Site hazards")
                for h in d["hazards"]:
                    st.markdown(f"{pill(h['severity'])} **{h['hazard']}**<br>Remedy: {h['remedy']}", unsafe_allow_html=True)
                st.download_button("Download JSON report", json.dumps(d, indent=2), "safety_report.json", "application/json")
            except (KeyError, TypeError) as exc:
                st.error(f"The model returned an unexpected structure (missing {exc}). Run the audit again.")
    else:
        st.info("Upload a photo to start the audit.")

# ---------------------------------------------------------------- tab 2
with tab2:
    up = st.file_uploader("Upload a concrete or wall surface photo", type=["jpg", "jpeg", "png"], key="crack_upload")
    if up:
        try:
            img = Image.open(up).convert("RGB")
        except Exception:
            st.error("That file could not be read as an image. Upload a JPG or PNG.")
            st.stop()
        c1, c2 = st.columns([1, 1.3])
        c1.image(img, use_container_width=True)
        if c2.button("Diagnose defect", type="primary"):
            with st.spinner("Analysing surface..."):
                st.session_state["crack"], st.session_state["crack_mode"] = analyze_image(CRACK_PROMPT, img, DEMO_CRACK)
        d = st.session_state.get("crack")
        if d:
            try:
                with c2:
                    a, b, c = st.columns(3)
                    with a: metric("Defect", d["defect_type"])
                    with b: metric("Width", f"{d['estimated_width_mm']} mm")
                    with c: metric("Severity", f"{d['severity_score']}/100")
                    st.markdown(f"**Severity:** {pill(d['severity'])} &nbsp; **Urgency:** {d['urgency']}", unsafe_allow_html=True)
                    st.write(d.get("notes", ""))
                x, y = st.columns(2)
                x.subheader("Root causes")
                for r in d["root_causes"]:
                    x.markdown(f"- {r}")
                y.subheader("Recommended repairs")
                for r in d["recommended_repairs"]:
                    y.markdown(f"- {r}")
                st.download_button("Download JSON report", json.dumps(d, indent=2), "crack_report.json", "application/json")
            except (KeyError, TypeError) as exc:
                st.error(f"The model returned an unexpected structure (missing {exc}). Run the diagnosis again.")
    else:
        st.info("Upload a surface photo to classify the defect.")

# ---------------------------------------------------------------- tab 3
with tab3:
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(COST_PER_SQFT))
    tier = c2.selectbox("Location tier", list(TIER_MULT))
    sqft = c1.number_input("Built-up area (sq ft)", 200, 500000, 1500, step=100)
    pct = c2.slider("Completion %", 0, 100, 40)

    budget = sqft * COST_PER_SQFT[stype] * TIER_MULT[tier]
    capex = budget * pct / 100
    # Asset value: finished market value scaled by completion, with a 15% under-construction discount until handover.
    market = sqft * MARKET_PER_SQFT[tier]
    asset = market * pct / 100 * (1 if pct == 100 else 0.85)
    steel_t = sqft * STEEL_KG_SQFT[stype] / 1000
    cement = sqft * CEMENT_BAGS_SQFT

    m = st.columns(4)
    with m[0]: metric("Total budget", inr(budget))
    with m[1]: metric("Capex incurred", inr(capex))
    with m[2]: metric("Current asset value", inr(asset))
    with m[3]: metric("Finished market value", inr(market))
    m = st.columns(2)
    with m[0]: metric("Steel required (total / used)", f"{steel_t:.1f} t / {steel_t*pct/100:.1f} t")
    with m[1]: metric("Cement required (total / used)", f"{cement:,.0f} / {cement*pct/100:,.0f} bags")

    st.markdown("**Milestone progress**")
    st.progress(pct / 100)
    current = [n for p, n in MILESTONES if pct >= p][-1]
    nxt = next(((p, n) for p, n in MILESTONES if p > pct), None)
    st.caption(f"Current phase: {current}" + (f". Next: {nxt[1]} at {nxt[0]}%." if nxt else ". Project complete."))

    st.subheader("Conceptual 3D rendering")
    style = st.text_input("Style notes", "modern Indian architecture, glass and concrete, golden hour")
    prompt = f"3D architectural render of a {stype} building, {sqft} sq ft, {style}, photorealistic, {pct}% constructed"
    st.code(prompt, language=None)
    if st.button("Generate rendering"):
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=640&model=flux&nologo=true"
        st.image(url, caption="Generated via Pollinations (Flux)", use_container_width=True)
    st.caption("Rates are indicative planning assumptions, not quotations. Verify with local contractors and registered valuers.")

# ---------------------------------------------------------------- tab 4
with tab4:
    w = st.radio("Today's weather", list(WEATHER), horizontal=True)
    for tip in WEATHER[w]:
        st.markdown(f'<div class="alert">{tip}</div>', unsafe_allow_html=True)

    st.subheader("Engineering assistant")
    hist = st.session_state.setdefault("chat", [])
    for msg in hist:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if q := st.chat_input("Ask about curing, materials, IS codes, safety..."):
        with st.chat_message("user"):
            st.write(q)
        with st.spinner("Thinking..."):
            ans = chat_reply(hist, q)
        hist += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]
        with st.chat_message("assistant"):
            st.write(ans)
    if hist and st.button("Clear conversation"):
        st.session_state["chat"] = []
        st.rerun()