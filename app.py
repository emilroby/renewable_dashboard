# app.py
# ──────────────────────────────────────────────────────────────────────────────
# Real Time Project Milestone Monitoring Dashboard
# Data sources:
#   1) "Milestones in RE projects.xlsx" (Sheet1) → Checkpoints & Milestones
#   2) "Quarterly_Report_on_Under_Construction_Renewable_Energy_Projects_as_on_June_2025.xlsx"
#      (or the variant with two dots) — ONLY Sheet 3 "Under Construction Projects"
#      → Under-construction projects; we temporarily assign them to checkpoints/milestones
# ──────────────────────────────────────────────────────────────────────────────

import re
import base64
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px

# ──────────────────────────────────────────────────────────────────────────────
# Page Config & Global Styles
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Real Time Project Milestone Monitoring Dashboard",
    layout="wide"
)

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 700px at 12% -10%, #F3FAF6 0%, transparent 60%),
    radial-gradient(1200px 700px at 90% 0%, #E8F3EE 0%, transparent 65%),
    linear-gradient(180deg, #FFFFFF 0%, #F7FBF9 100%);
}
.stApp { font-family: 'Poppins', sans-serif; }

/* Title */
.main-title{
  font-size: 34px !important;
  font-weight: 800 !important;
  color: #0F4237 !important;
  text-align: center;
  margin: 0;
  text-shadow: 0 1px 0 rgba(255,255,255,0.7);
}

/* Section headings */
.subheader, .section-title {
  font-size: 26px !important;
  font-weight: 700 !important;
  color: #1b5e20 !important;
  margin-top: 16px;
  margin-bottom: 10px;
  text-align: center;
}

/* Buttons used as cards */
div.stButton > button {
  border-radius: 16px !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.25 !important;
  padding: 18px 22px !important;
  background-color: #ffffff !important;
  border: 2px solid #1b5e20 !important;
  color: #0F4237 !important;
  box-shadow: 0 8px 22px rgba(16,40,32,0.08);
  transition: all 0.18s ease-in-out;
  width: 100%;
  white-space: normal !important;
  word-break: break-word !important;
  text-align: left !important;
}
div.stButton > button:hover {
  background-color: #1b5e20 !important;
  color: #ffffff !important;
  transform: translateY(-1px);
}

/* KPI/Panel cards */
.card {
  border-radius: 16px;
  padding: 16px 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f9fcfa 100%);
  border: 1px solid #e5ece8;
  box-shadow: 0 10px 22px rgba(16,40,32,0.06);
}
.kpi-value{
  font-size: 28px; font-weight: 800; color:#0F4237; line-height:1.1; margin-top:6px;
}
.kpi-label{
  font-size: 12px; font-weight: 600; color:#2f6a57; text-transform: uppercase; letter-spacing:.5px;
}

/* Tighten plot paddings to reduce gaps */
.js-plotly-plot .plotly .main-svg { background: rgba(0,0,0,0) !important; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────────────────────
for k, v in {"selected_state": None, "selected_checkpoint": None, "selected_milestone": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────────────
# TOP: Live Date/Time (extreme left)
# ──────────────────────────────────────────────────────────────────────────────
components.html("""
  <div style="font-family:Poppins,system-ui,Arial; display:flex; align-items:center; gap:18px;
              padding:2px 0 6px 2px; font-weight:700; color:#0F4237; font-size:14px; justify-content:flex-start;">
    <span id="live-date"></span><span style="opacity:.5">|</span><span id="live-time"></span>
  </div>
  <script>
    (function(){
      function render(){
        const now = new Date();
        const opts = { timeZone:'Asia/Kolkata', year:'numeric', month:'long', day:'2-digit',
                       hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false };
        const parts = new Intl.DateTimeFormat('en-GB', opts).formatToParts(now)
                      .reduce((a,p)=>{a[p.type]=p.value; return a;}, {});
        const day = parts.day; const month = (parts.month||'').toLowerCase(); const year = parts.year;
        const time = `${parts.hour}:${parts.minute}:${parts.second} IST`;
        document.getElementById('live-date').textContent = `${day} - ${month} - ${year}`;
        document.getElementById('live-time').textContent = time;
      }
      render(); setInterval(render, 1000);
    })();
  </script>
""", height=30)

# ──────────────────────────────────────────────────────────────────────────────
# Logos + Title Row (inline)
# ──────────────────────────────────────────────────────────────────────────────
def find_logo(possible_names):
    cwd = Path(".").resolve()
    for p in [cwd] + [p for p in cwd.iterdir() if p.is_dir()]:
        for name in possible_names:
            exact = p / name
            if exact.exists():
                return str(exact)
        for child in p.glob("*"):
            if child.is_file():
                for name in possible_names:
                    if child.name.lower() == name.lower():
                        return str(child)
    return None

def img_tag(path: str, height_px: int = 65, alt: str = "") -> str:
    try:
        b64 = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
        ext = Path(path).suffix.lower()
        mime = "image/png" if ext in [".png"] else ("image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png")
        return f"<img alt='{alt}' src='data:{mime};base64,{b64}' style='height:{height_px}px;'/>"
    except Exception:
        return ""

MNRE_LOGO = find_logo(["MNRE.png", "mnre.png", "MNRE.PNG"])
NSEFI_LOGO = find_logo(["12th_year_anniversary_logo_transparent.png",
                        "12th_year_anniversary_logo_transparent.PNG"])

col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    if MNRE_LOGO:
        st.markdown(img_tag(MNRE_LOGO, height_px=65, alt="MNRE"), unsafe_allow_html=True)
with col2:
    st.markdown("<h1 class='main-title'>Real Time Project Milestone Monitoring Dashboard</h1>", unsafe_allow_html=True)
with col3:
    if NSEFI_LOGO:
        st.markdown(img_tag(NSEFI_LOGO, height_px=65, alt="NSEFI"), unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def pickcol(cols, *candidates):
    cols = [str(c) for c in cols]
    low = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        k = str(cand).lower().strip()
        if k in low:
            return low[k]
    for cand in candidates:
        k = str(cand).lower().strip()
        for c in cols:
            if k in c.lower():
                return c
    return None

def norm_text_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    s = s.replace({"nan": pd.NA, "None": pd.NA})
    s = s.str.replace(r"\s+", " ", regex=True)
    return s

def norm_key(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).lower().strip().replace("&","and")
    s = re.sub(r"[^a-z ]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def parse_mw(val):
    if pd.isna(val):
        return pd.NA
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val)
    s = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(s) if s else pd.NA
    except Exception:
        return pd.NA

# ──────────────────────────────────────────────────────────────────────────────
# Milestones (Sheet1)
# ──────────────────────────────────────────────────────────────────────────────
MILES_FILE = "Milestones in RE projects.xlsx"

@st.cache_data
def load_milestones(file_path: str):
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df = df.rename(columns={"Step No": "Step_No", "Checkpoints": "Checkpoint", "Milestones": "Milestone"})
    df = df.dropna(how="all")
    for c in ["Checkpoint", "Milestone"]:
        df[c] = df[c].astype(str).str.strip()
    df["Checkpoint"] = df["Checkpoint"].replace({"nan": pd.NA}).ffill()
    if "Step_No" in df.columns:
        df = df.sort_values("Step_No")
    return df.reset_index(drop=True)

if Path(MILES_FILE).exists():
    milestones_df = load_milestones(MILES_FILE)
else:
    milestones_df = pd.DataFrame()
    st.error("⚠️ Add 'Milestones in RE projects.xlsx' in the project root.")

if not milestones_df.empty:
    cp_order_df = (milestones_df[["Step_No","Checkpoint"]]
                   .dropna(subset=["Checkpoint"])
                   .drop_duplicates(subset=["Checkpoint"], keep="first"))
    CHECKPOINT_ORDER = (cp_order_df.sort_values("Step_No")["Checkpoint"].tolist()
                        if "Step_No" in cp_order_df.columns else cp_order_df["Checkpoint"].tolist())
    # Make sure milestone lists have no NaN/empty values
    CP_TO_MS = {cp: [m for m in milestones_df.loc[milestones_df["Checkpoint"] == cp, "Milestone"]
                     .astype(str).str.strip().tolist() if str(m).strip().lower() != "nan"]
                for cp in CHECKPOINT_ORDER}
else:
    CHECKPOINT_ORDER, CP_TO_MS = [], {}

# ──────────────────────────────────────────────────────────────────────────────
# Under-construction Excel — ONLY Sheet 3: “Under Construction Projects”
# ──────────────────────────────────────────────────────────────────────────────
UC_FILE_CANDIDATES = [
    "Quarterly_Report_on_Under_Construction_Renewable_Energy_Projects_as_on_June_2025.xlsx",
    "Quarterly_Report_on_Under_Construction_Renewable_Energy_Projects_as_on_June_2025..xlsx",
]

def find_uc_file():
    for cand in UC_FILE_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None

def read_uc_ucprojects_sheet(path: str):
    xl = pd.ExcelFile(path)
    wanted = None
    for nm in xl.sheet_names:
        if str(nm).strip().lower() == "under construction projects":
            wanted = nm
            break
    if wanted is None:
        raise ValueError("The workbook does not contain a sheet named 'Under Construction Projects'.")
    df = xl.parse(wanted)
    df.rename(columns=lambda x: str(x).strip().replace("\n"," ").replace("  "," "), inplace=True)
    return df

def normalize_project_type(v: str) -> str:
    t = norm_key(v)
    if any(k in t for k in ["hybrid","mix"]): return "Hybrid"
    if any(k in t for k in ["wind"]):   return "Wind"
    if any(k in t for k in ["solar","pv"]): return "Solar"
    if any(k in t for k in ["hydro","hydel","psp","pumped"]): return "Hydro/PSP"
    if any(k in t for k in ["battery","storage","bess"]): return "Storage"
    return "Other"

CPSU_TOKENS = [
    "ntpc","nhpc","seci","nlc","sgel","sjvn","gail","iocl","ongc","bhel",
    "pfc","rec","railway","indian oil","powergrid","pgcil","sail","coal india","cil"
]

def classify_owner(developer: str) -> str:
    s = norm_key(developer)
    return "CPSU" if any(tok in s for tok in CPSU_TOKENS) else "Private"

@st.cache_data
def load_uc_clean(path: str):
    raw = read_uc_ucprojects_sheet(path)

    cols = [str(c) for c in raw.columns]
    c_serial  = pickcol(cols, "S. No", "S No", "Sr. No", "Sl No", "Serial", "Sl. No.")
    c_project = pickcol(cols, "Project Name","Project","Name")
    c_state   = pickcol(cols, "State", "State/UT", "Location State")
    c_dev     = pickcol(cols, "Developer","Implementing Agency","Agency","Owner","Developer Name")
    c_type    = pickcol(cols, "Project Type","Type","Technology","Mode")
    c_cap     = pickcol(cols, "Capacity (MW)","Capacity MW","Capacity in MW","Capacity")
    c_cod     = pickcol(cols, "COD","Expected COD","Date of Commissioning","Start Date","Date")

    df = pd.DataFrame()
    df["Serial"]       = pd.to_numeric(raw[c_serial], errors="coerce") if c_serial else pd.NA
    df["Project_Name"] = norm_text_series(raw[c_project]) if c_project else pd.NA
    df["State"]        = norm_text_series(raw[c_state])   if c_state   else pd.NA
    df["Developer"]    = norm_text_series(raw[c_dev])     if c_dev     else pd.NA
    df["Project_Type"] = norm_text_series(raw[c_type])    if c_type    else pd.NA
    df["Capacity_MW"]  = raw[c_cap].apply(parse_mw) if c_cap else pd.NA
    df["Date"]         = pd.to_datetime(raw[c_cod], errors="coerce") if c_cod else pd.NaT

    # Drop total/blank rows
    mask_total = (df["Project_Name"].str.contains("total", case=False, na=False)) | \
                 (df["State"].str.contains("total", case=False, na=False))
    df = df[~mask_total]
    df = df.dropna(how="all", subset=["Project_Name","State","Capacity_MW"])

    # Normalizations / derived fields
    df["Project_Type"] = df["Project_Type"].fillna("").apply(normalize_project_type)
    df["Owner_Class"]  = df["Developer"].fillna("").apply(classify_owner)
    df["Developer_norm"] = (df["Developer"].fillna("")
                            .str.lower().str.strip().str.replace(r"\s+"," ", regex=True))

    df["Project_Row"] = 1
    return df.reset_index(drop=True)

UC_FILE = find_uc_file()
if UC_FILE:
    try:
        uc_df = load_uc_clean(UC_FILE)
    except Exception as e:
        uc_df = pd.DataFrame()
        st.error(f"Could not load Under-Construction data: {e}")
else:
    uc_df = pd.DataFrame()
    st.info("Add the Quarterly Under-Construction Excel (we only read Sheet 3: 'Under Construction Projects').")

# ──────────────────────────────────────────────────────────────────────────────
# Randomly assign checkpoints/milestones (temporary)
# ──────────────────────────────────────────────────────────────────────────────
def assign_random_process(df_uc: pd.DataFrame, checkpoints: list[str], cp_to_ms: dict):
    if df_uc.empty or not checkpoints:
        return df_uc
    rng = random.Random(42)
    ms_choices = {cp: ([m for m in ms if str(m).strip()] or ["General"]) for cp, ms in cp_to_ms.items()}
    for cp in checkpoints:
        ms_choices.setdefault(cp, ["General"])
    start_window = datetime.now() - timedelta(days=730)
    span = max(1, (datetime.now() - start_window).days)

    cps, mss, dates = [], [], []
    for _ in range(len(df_uc)):
        cp = rng.choice(checkpoints)
        ms = rng.choice(ms_choices[cp])
        d  = start_window + timedelta(days=rng.randint(0, span))
        cps.append(cp); mss.append(ms); dates.append(d.date())

    out = df_uc.copy()
    out["Checkpoint"] = pd.Series(cps).fillna("Unassigned")
    out["Milestone"]  = pd.Series(mss).fillna("Unassigned")
    out["Milestone_Start_Date"] = dates
    return out

assigned_df = assign_random_process(uc_df, CHECKPOINT_ORDER, CP_TO_MS)
# Ensure no NaN visible anywhere for these two columns
if not assigned_df.empty:
    assigned_df["Checkpoint"] = assigned_df["Checkpoint"].astype(str).replace({"nan":"Unassigned"}).fillna("Unassigned")
    assigned_df["Milestone"]  = assigned_df["Milestone"].astype(str).replace({"nan":"Unassigned"}).fillna("Unassigned")

# ──────────────────────────────────────────────────────────────────────────────
# UI: Checkpoints & Milestones
# ──────────────────────────────────────────────────────────────────────────────
def render_checkpoints_row():
    st.markdown("<h2 class='subheader'>Project Process Workflow</h2>", unsafe_allow_html=True)
    if not CHECKPOINT_ORDER:
        st.info("Milestones file not found/empty.")
        return
    cols = st.columns(len(CHECKPOINT_ORDER))
    for i, cp in enumerate(CHECKPOINT_ORDER, start=1):
        count = int(assigned_df[assigned_df["Checkpoint"] == cp].shape[0]) if not assigned_df.empty else 0
        label = f"{i}. {cp}\n{count} projects"
        with cols[i-1]:
            if st.button(label, key=f"cp_btn_{i}", use_container_width=True):
                if st.session_state.selected_checkpoint == cp:
                    st.session_state.selected_checkpoint = None
                    st.session_state.selected_milestone = None
                else:
                    st.session_state.selected_checkpoint = cp
                    st.session_state.selected_milestone = None

def render_milestones_grid(cp: str, cols_per_row: int = 4):
    if not cp: return
    # filter out any empty/placeholder values
    ms_list = [m for m in CP_TO_MS.get(cp, []) if str(m).strip()]
    if not ms_list:
        st.info("No milestones defined for this checkpoint.")
        return
    cp_index = CHECKPOINT_ORDER.index(cp) + 1
    st.markdown(f"<h2 class='section-title'>Milestones — {cp}</h2>", unsafe_allow_html=True)
    j = 1
    for start in range(0, len(ms_list), cols_per_row):
        row = ms_list[start:start+cols_per_row]
        cols = st.columns(len(row))
        for c_i, m in enumerate(row):
            m_count = int(assigned_df[assigned_df["Milestone"] == m].shape[0]) if not assigned_df.empty else 0
            label = f"{cp_index}.{j} {m}\n{m_count} projects"
            with cols[c_i]:
                if st.button(label, key=f"ms_btn_{cp_index}_{j}", use_container_width=True):
                    st.session_state.selected_milestone = (None if st.session_state.selected_milestone == m else m)
            j += 1

# ──────────────────────────────────────────────────────────────────────────────
# KPI + Snapshot dashboard (filters + multiple visualizations)
# ──────────────────────────────────────────────────────────────────────────────
def render_kpis(df: pd.DataFrame):
    cap = pd.to_numeric(df["Capacity_MW"], errors="coerce").fillna(0.0)
    total_projects = int(df["Project_Row"].sum()) if "Project_Row" in df.columns else len(df)
    total_capacity = int(cap.sum())
    avg_capacity   = round(float(cap.mean()), 2) if len(cap) else 0.0
    type_counts = df["Project_Type"].value_counts(dropna=True)
    solar_n  = int(type_counts.get("Solar", 0))
    wind_n   = int(type_counts.get("Wind", 0))
    hybrid_n = int(type_counts.get("Hybrid", 0))

    c1, c2, c3, c4, c5 = st.columns(5)
    for c, label, value in [
        (c1, "Total Projects", f"{total_projects:,}"),
        (c2, "Total Capacity (MW)", f"{total_capacity:,}"),
        (c3, "Avg Capacity / Project", f"{avg_capacity}"),
        (c4, "Solar Projects", f"{solar_n:,}"),
        (c5, "Wind / Hybrid", f"{wind_n:,} / {hybrid_n:,}"),
    ]:
        with c:
            st.markdown(
                f"<div class='card'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>",
                unsafe_allow_html=True
            )

def render_snapshot(df: pd.DataFrame):
    if df.empty:
        return
    st.markdown("<h2 class='section-title'>RE projects under construction snapshot</h2>", unsafe_allow_html=True)

    # Inline dashboard filter — Project Type; manual choices only
    ft = st.selectbox(
        "Filter — Project Type",
        ["Choose an option", "Solar", "Wind", "Hybrid"],
        index=0,
    )
    fdf = df.copy()
    if ft != "Choose an option":
        fdf = fdf[fdf["Project_Type"] == ft]

    # KPIs
    render_kpis(fdf)

    # Row 1: Donut pie (type) + CPSU vs Private
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        cap_type = (fdf.groupby("Project_Type", as_index=False)["Capacity_MW"].sum()
                      .sort_values("Capacity_MW", ascending=False))
        if not cap_type.empty:
            cap_type["Capacity_MW"] = pd.to_numeric(cap_type["Capacity_MW"], errors="coerce").fillna(0.0)
            fig = px.pie(cap_type, names="Project_Type", values="Capacity_MW", hole=0.45,
                         title="Capacity share by Project Type")
            fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=360, legend_traceorder='normal')
            st.plotly_chart(fig, use_container_width=True)
    with r1c2:
        cls = (fdf.groupby("Owner_Class", as_index=False)
                 .agg(Capacity_MW=("Capacity_MW","sum"), Projects=("Project_Row","sum")))
        if not cls.empty:
            cls["Capacity_MW"] = pd.to_numeric(cls["Capacity_MW"], errors="coerce").fillna(0.0)
            fig = px.bar(cls, x="Owner_Class", y="Capacity_MW", text="Projects",
                         title="CPSU vs Private (Capacity with projects count)")
            fig.update_traces(textposition="outside")
            fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=360)
            st.plotly_chart(fig, use_container_width=True)

    # Row 2: Capacity by state + Projects by state
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        state_cap = (fdf.groupby("State", as_index=False)["Capacity_MW"].sum()
                       .sort_values("Capacity_MW", ascending=False))
        if not state_cap.empty:
            state_cap["Capacity_MW"] = pd.to_numeric(state_cap["Capacity_MW"], errors="coerce").fillna(0.0)
            fig = px.bar(state_cap, x="State", y="Capacity_MW", title="Capacity by State")
            fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=380)
            st.plotly_chart(fig, use_container_width=True)
    with r2c2:
        state_proj = (fdf.groupby("State", as_index=False)["Project_Row"].sum()
                        .rename(columns={"Project_Row":"Projects"})
                        .sort_values("Projects", ascending=False))
        if not state_proj.empty:
            fig = px.bar(state_proj, x="State", y="Projects", title="Projects by State")
            fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=380)
            st.plotly_chart(fig, use_container_width=True)

    # Row 3 (your request): Top developers (LEFT) + Projects over time (RIGHT) in a dedicated wide row
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        dev_cap = (fdf.assign(Developer_display=fdf["Developer"].fillna(fdf["Developer_norm"]))
                     .groupby("Developer_display", as_index=False)["Capacity_MW"].sum()
                     .sort_values("Capacity_MW", ascending=False))
        if not dev_cap.empty:
            dev_cap["Capacity_MW"] = pd.to_numeric(dev_cap["Capacity_MW"], errors="coerce").fillna(0.0)
            fig = px.bar(dev_cap.head(15), x="Capacity_MW", y="Developer_display",
                         orientation="h", title="Top Developers by Capacity (MW)")
            fig.update_layout(yaxis_title="Developer", xaxis_title="Capacity (MW)",
                              margin=dict(l=6,r=6,t=40,b=6), height=420)
            st.plotly_chart(fig, use_container_width=True)
    with r3c2:
        if "Date" in fdf.columns and fdf["Date"].notna().any():
            ts = fdf.dropna(subset=["Date"]).copy()
            ts["Month"] = pd.to_datetime(ts["Date"]).dt.to_period("M").dt.to_timestamp()
            ts_agg = ts.groupby("Month", as_index=False)["Project_Row"].sum().rename(columns={"Project_Row":"Projects"})
            if not ts_agg.empty:
                fig = px.line(ts_agg, x="Month", y="Projects", markers=True,
                              title="Projects over time")
                fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=420)
                st.plotly_chart(fig, use_container_width=True)

    # Row 4: Stacked (full width) — capacity by type within top states
    top_states = (fdf.groupby("State", as_index=False)["Capacity_MW"].sum()
                    .sort_values("Capacity_MW", ascending=False).head(10)["State"])
    stacked = (fdf[fdf["State"].isin(top_states)]
                .groupby(["State","Project_Type"], as_index=False)["Capacity_MW"].sum())
    if not stacked.empty:
        stacked["Capacity_MW"] = pd.to_numeric(stacked["Capacity_MW"], errors="coerce").fillna(0.0)
        fig = px.bar(stacked, x="State", y="Capacity_MW", color="Project_Type",
                     title="Capacity by Type within Top States", barmode="stack")
        fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=380, legend_traceorder='normal')
        st.plotly_chart(fig, use_container_width=True)

    # Row 5: Bubble full width
    sp = (fdf.groupby("State", as_index=False)
            .agg(Projects=("Project_Row","sum"), Capacity_MW=("Capacity_MW","sum")))
    if not sp.empty:
        sp["Capacity_MW"] = pd.to_numeric(sp["Capacity_MW"], errors="coerce").fillna(0.0).astype(float)
        fig = px.scatter(sp, x="Projects", y="Capacity_MW", size="Capacity_MW",
                         hover_name="State", title="Capacity vs Projects by State")
        fig.update_layout(margin=dict(l=6,r=6,t=40,b=6), height=380)
        st.plotly_chart(fig, use_container_width=True)

    # Data export
    st.download_button(
        "Download filtered projects (CSV)",
        data=fdf[["Project_Name","Developer","Owner_Class","Project_Type",
                  "Capacity_MW","State","Checkpoint","Milestone",
                  "Milestone_Start_Date","Date"]].to_csv(index=False).encode("utf-8"),
        file_name="under_construction_projects_filtered.csv",
        mime="text/csv",
        use_container_width=True
    )

# ──────────────────────────────────────────────────────────────────────────────
# PAGE
# ──────────────────────────────────────────────────────────────────────────────
if not milestones_df.empty and not assigned_df.empty and CHECKPOINT_ORDER:
    # 1) Checkpoints single line
    render_checkpoints_row()

    # 2) Milestones grid (toggle)
    if st.session_state.selected_checkpoint:
        render_milestones_grid(st.session_state.selected_checkpoint, cols_per_row=4)

    # 3) Space then snapshot dashboard
    st.markdown("<br>", unsafe_allow_html=True)

    # Optional table when a milestone is clicked
    current_df = assigned_df.copy()
    if st.session_state.get("selected_checkpoint"):
        current_df = current_df[current_df["Checkpoint"] == st.session_state.selected_checkpoint]
    if st.session_state.get("selected_milestone"):
        current_df = current_df[current_df["Milestone"] == st.session_state.selected_milestone]
        # Ensure no NaN shown
        for c in ["Checkpoint","Milestone"]:
            if c in current_df.columns:
                current_df[c] = current_df[c].fillna("Unassigned").replace({"nan":"Unassigned"})
        st.dataframe(
            current_df[["Project_Name","Developer","Owner_Class","Project_Type",
                        "Capacity_MW","State","Checkpoint","Milestone",
                        "Milestone_Start_Date","Date"]].reset_index(drop=True),
            use_container_width=True
        )

    # 4) Snapshot dashboard (no map)
    render_snapshot(current_df)

else:
    if milestones_df.empty:
        st.info("Add 'Milestones in RE projects.xlsx' (Sheet1 with Step No / Checkpoints / Milestones).")
    if assigned_df.empty:
        st.info("Add the Quarterly Under-Construction Excel (we only read Sheet 3: 'Under Construction Projects').")

# ------------------------------ ACTIVITY LOGS (drop-in) ------------------------------
# Paste this block once near the bottom of app.py (after your imports/widgets).
import os, json, uuid, logging, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
import streamlit as st

# --- Settings
LOG_DIR = Path("logs")
RETENTION_DAYS = 90            # delete logs older than this
APP_TZ = timezone(timedelta(hours=5, minutes=30))  # IST

def _ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def _current_log_path() -> str:
    _ensure_log_dir()
    today = datetime.now(APP_TZ).strftime("%Y-%m-%d")
    return str(LOG_DIR / f"activity_{today}.txt")

def _get_session_id() -> str:
    if "sid" not in st.session_state:
        st.session_state.sid = uuid.uuid4().hex
    return st.session_state.sid

def _get_logger() -> logging.Logger:
    """
    Create or reuse a logger that writes JSON lines to today's file.
    Ensures no duplicate handlers across reruns.
    """
    _ensure_log_dir()
    path = _current_log_path()

    logger = logging.getLogger("activity")
    logger.setLevel(logging.INFO)

    # If a FileHandler already points to today's file, reuse it; otherwise refresh.
    def _handler_points_to_today(h):
        return isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == os.path.abspath(path)

    if not any(_handler_points_to_today(h) for h in logger.handlers):
        # remove old file handlers
        logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.FileHandler)]
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        # we only write JSON messages, so keep formatter simple
        fh.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(fh)

    return logger

def log_event(event: str, **fields):
    """
    Write one JSON line (UTF-8) with UTC+IST dual timestamps, session id and fields.
    """
    logger = _get_logger()
    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    now_ist = now_utc.astimezone(APP_TZ)

    record = {
        "ts_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "ts_ist": now_ist.isoformat(),
        "session_id": _get_session_id(),
        "event": event,
        "fields": fields,
    }
    try:
        logger.info(json.dumps(record, ensure_ascii=False))
    except Exception as e:
        # Last resort: avoid breaking the app if logging fails
        print("LOGGING_ERROR:", e)

def _prune_old_logs(days=RETENTION_DAYS):
    _ensure_log_dir()
    cutoff = datetime.now(APP_TZ) - timedelta(days=days)
    for p in LOG_DIR.glob("activity_*.txt"):
        try:
            # parse date from filename
            stamp = p.stem.split("_")[-1]  # 'YYYY-MM-DD'
            fdate = datetime.strptime(stamp, "%Y-%m-%d").replace(tzinfo=APP_TZ)
            if fdate < cutoff:
                p.unlink(missing_ok=True)
        except Exception:
            # ignore unparsable files
            pass

# --- Auto log a page view once per session
if not st.session_state.get("_logged_pageview"):
    log_event("page_view", path=st.query_params.to_dict() if hasattr(st, "query_params") else {})
    st.session_state["_logged_pageview"] = True

# --- Optional: watch common session-state keys from your app and log on change
for _watch_key in ("selected_checkpoint", "selected_milestone", "selected_state"):
    if _watch_key in st.session_state:
        last_key = f"_last_logged__{_watch_key}"
        cur_val = st.session_state[_watch_key]
        if st.session_state.get(last_key) != cur_val:
            log_event("state_change", key=_watch_key, value=cur_val)
            st.session_state[last_key] = cur_val

# --- Keep logs tidy
_prune_old_logs()

# --- Sidebar: downloads & preview
with st.sidebar.expander("📜 Activity logs", expanded=False):
    try:
        # Download today's log
        today_path = _current_log_path()
        if os.path.exists(today_path):
            with open(today_path, "rb") as f:
                st.download_button(
                    "Download today's log (.txt)",
                    data=f.read(),
                    file_name=os.path.basename(today_path),
                    mime="text/plain",
                    use_container_width=True,
                )
        else:
            st.caption("No log file created yet today.")

        # Download ALL logs as ZIP
        if os.path.isdir(LOG_DIR) and len(os.listdir(LOG_DIR)) > 0:
            zip_basename = f"logs_bundle_{datetime.now(APP_TZ).strftime('%Y%m%d_%H%M')}"
            shutil.make_archive(zip_basename, "zip", LOG_DIR)  # creates '<basename>.zip'
            zip_path = f"{zip_basename}.zip"
            with open(zip_path, "rb") as zf:
                st.download_button(
                    "Download ALL logs (.zip)",
                    data=zf.read(),
                    file_name=os.path.basename(zip_path),
                    mime="application/zip",
                    use_container_width=True,
                )
            # cleanup temp zip
            try:
                os.remove(zip_path)
            except Exception:
                pass

        # Tail preview
        n = st.slider("Preview last N lines", 10, 500, 50)
        if os.path.exists(today_path):
            try:
                with open(today_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                tail = "".join(lines[-n:])
                st.code(tail or "(file exists but is currently empty)", language="json")
            except Exception as e:
                st.caption(f"(Could not preview log: {e})")

        # Simple event to test logging from the UI
        if st.button("Write a test log line", use_container_width=True):
            log_event("test_click", note="user pressed test button")
            st.success("Wrote a test event to today's log.")

    except Exception as e:
        st.warning(f"Log tools unavailable: {e}")
# ---------------------------- END ACTIVITY LOGS (drop-in) ----------------------------