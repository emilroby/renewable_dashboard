# app.py
import base64
import streamlit as st
import pandas as pd
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

# Viz
import plotly.express as px
from streamlit_folium import st_folium
import folium
import streamlit.components.v1 as components

# ---------------------------------
# Page Config
# ---------------------------------
st.set_page_config(
    page_title="Real Time Project Milestone Monitoring Dashboard",
    layout="wide"
)

# ---------------------------------
# Global Styles
# ---------------------------------
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
  margin-top: 20px;
  margin-bottom: 14px;
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
  font-size: 32px; font-weight: 800; color:#0F4237; line-height:1.1; margin-top:6px;
}
.kpi-label{
  font-size: 12px; font-weight: 600; color:#2f6a57; text-transform: uppercase; letter-spacing:.5px;
}
</style>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ---------------------------------
# Session state
# ---------------------------------
if "selected_state" not in st.session_state:
    st.session_state.selected_state = None
if "selected_checkpoint" not in st.session_state:
    st.session_state.selected_checkpoint = None
if "selected_milestone" not in st.session_state:
    st.session_state.selected_milestone = None

# ---------------------------------
# Logo finder + HTML tag helper
# ---------------------------------
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

# ---------------------------------
# TOP: Live Date/Time (extreme left)
# ---------------------------------
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

# ---------------------------------
# Logos + Title Row (inline)
# ---------------------------------
col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    if MNRE_LOGO:
        st.markdown(img_tag(MNRE_LOGO, height_px=65, alt="MNRE"), unsafe_allow_html=True)
with col2:
    st.markdown("<h1 class='main-title'>Real Time Project Milestone Monitoring Dashboard</h1>", unsafe_allow_html=True)
with col3:
    if NSEFI_LOGO:
        st.markdown(img_tag(NSEFI_LOGO, height_px=65, alt="NSEFI"), unsafe_allow_html=True)

# ---------------------------------
# Load milestones dynamically + Dummy projects
# ---------------------------------
FILE_PATH = "Milestones in RE projects.xlsx"
FILE_MTIME = Path(FILE_PATH).stat().st_mtime if Path(FILE_PATH).exists() else 0

@st.cache_data
def load_milestones_clean(file_path: str, file_mtime: float):
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df = df.rename(columns={"Step No": "Step_No", "Checkpoints": "Checkpoint", "Milestones": "Milestone"})
    df = df.dropna(how="all")
    for c in ["Checkpoint", "Milestone"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["Checkpoint"] = df["Checkpoint"].replace({"nan": pd.NA}).ffill()
    if "Step_No" in df.columns:
        df = df.sort_values("Step_No")
    return df.reset_index(drop=True)

if Path(FILE_PATH).exists():
    milestones_df = load_milestones_clean(FILE_PATH, FILE_MTIME)
else:
    milestones_df = pd.DataFrame()

# Dynamic checkpoint order from Excel
if not milestones_df.empty:
    cp_order_df = (
        milestones_df[["Step_No", "Checkpoint"]]
        .dropna(subset=["Checkpoint"])
        .drop_duplicates(subset=["Checkpoint"], keep="first")
    )
    if "Step_No" in cp_order_df.columns:
        CHECKPOINT_ORDER = cp_order_df.sort_values("Step_No")["Checkpoint"].tolist()
    else:
        CHECKPOINT_ORDER = cp_order_df["Checkpoint"].tolist()
else:
    CHECKPOINT_ORDER = []

def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(days=random.randint(0, max(1, delta.days)))

@st.cache_data
def generate_projects(n=900, mdf: pd.DataFrame = None):
    developers = ["Adani Green", "ReNew Power", "Tata Power", "Azure", "NTPC RE"]
    states = ["Rajasthan", "Gujarat", "Maharashtra", "Karnataka", "Tamil Nadu"]
    if mdf is None or mdf.empty:
        return pd.DataFrame()
    valid_rows = mdf[mdf["Milestone"].notna() & (mdf["Milestone"].str.len() > 0)]
    start_window = datetime.now() - timedelta(days=730)
    end_window = datetime.now()
    projects = []
    for i in range(1, n+1):
        row = valid_rows.sample(1).iloc[0]
        projects.append({
            "Project_ID": f"P{i:04d}",
            "Project_Name": f"Project_{i}",
            "Developer": random.choice(developers),
            "Capacity_MW": random.choice([50, 100, 200, 500]),
            "State": random.choice(states),
            "Checkpoint": row["Checkpoint"],
            "Milestone": row["Milestone"],
            "Milestone_Start_Date": random_date(start_window, end_window).date()
        })
    return pd.DataFrame(projects)

projects_df = generate_projects(900, milestones_df) if not milestones_df.empty else pd.DataFrame()

# ---------------------------------
# Checkpoints row (single line)
# ---------------------------------
def render_checkpoints_row():
    st.markdown("<h2 class='subheader'>Project Process Workflow</h2>", unsafe_allow_html=True)
    cps = CHECKPOINT_ORDER
    if not cps: return
    cols = st.columns(len(cps))
    for i, cp in enumerate(cps, start=1):
        count = int(projects_df[projects_df["Checkpoint"] == cp].shape[0])
        label = f"{i}. {cp}\n{count} projects"
        with cols[i-1]:
            if st.button(label, key=f"cp_btn_{i}", use_container_width=True):
                if st.session_state.selected_checkpoint == cp:
                    st.session_state.selected_checkpoint = None
                    st.session_state.selected_milestone = None
                else:
                    st.session_state.selected_checkpoint = cp
                    st.session_state.selected_milestone = None

# ---------------------------------
# Milestones grid (wrap)
# ---------------------------------
def render_milestones_grid(cp: str, cols_per_row: int = 4):
    if not cp: return
    cp_index = CHECKPOINT_ORDER.index(cp) + 1
    ms_series = milestones_df.loc[milestones_df["Checkpoint"] == cp, "Milestone"].dropna().astype(str).str.strip()
    ms_unique = [m for m in ms_series.unique().tolist() if m]
    if not ms_unique: return
    st.markdown(f"<h2 class='section-title'>Milestones — {cp}</h2>", unsafe_allow_html=True)
    j = 1
    for start in range(0, len(ms_unique), cols_per_row):
        row = ms_unique[start:start+cols_per_row]
        cols = st.columns(len(row))
        for c_i, m in enumerate(row):
            m_count = int(projects_df[projects_df["Milestone"] == m].shape[0])
            label = f"{cp_index}.{j} {m}\n{m_count} projects"
            with cols[c_i]:
                if st.button(label, key=f"ms_btn_{cp_index}_{j}", use_container_width=True):
                    st.session_state.selected_milestone = (None if st.session_state.selected_milestone == m else m)
            j += 1

# ---------------------------------
# Map (capacity bubbles)
# ---------------------------------
STATE_CENTROIDS = {
    "Rajasthan":  (27.0238, 74.2179),
    "Gujarat":    (22.2587, 71.1924),
    "Maharashtra":(19.7515, 75.7139),
    "Karnataka":  (15.3173, 75.7139),
    "Tamil Nadu": (11.1271, 78.6569),
}

def render_state_bubble_map(df: pd.DataFrame):
    st.markdown("<h2 class='section-title'>India — Projects by State</h2>", unsafe_allow_html=True)
    if df.empty: return
    agg = df.groupby("State", as_index=False).agg(Projects=("Project_ID", "count"),
                                                 Capacity_MW=("Capacity_MW", "sum"))
    m = folium.Map(location=[22.97, 78.65], zoom_start=5, tiles="cartodbpositron")
    max_cap = max(agg["Capacity_MW"]) if not agg.empty else 1
    for state, (lat, lon) in STATE_CENTROIDS.items():
        row = agg[agg["State"] == state]
        capacity = int(row["Capacity_MW"].iloc[0]) if not row.empty else 0
        radius = 12 + (capacity / max_cap) * 38 if max_cap > 0 else 12
        popup_html = f"<b>{state}</b><br>Capacity: {capacity} MW"
        folium.CircleMarker(location=(lat, lon), radius=radius, color="#1E6A54",
                            fill=True, fill_color="#1E6A54", fill_opacity=0.65,
                            tooltip=f"{state} — {capacity} MW",
                            popup=folium.Popup(popup_html, max_width=260)).add_to(m)
    st_folium(m, width=None, height=520)

# ---------------------------------
# KPI Cards + Dashboard
# ---------------------------------
def render_kpis(df: pd.DataFrame):
    total_projects = len(df)
    total_capacity = int(df["Capacity_MW"].sum()) if not df.empty else 0
    avg_capacity = round(df["Capacity_MW"].mean(), 2) if not df.empty else 0
    unique_checkpoints = df["Checkpoint"].nunique() if not df.empty else 0
    unique_milestones = df["Milestone"].nunique() if not df.empty else 0
    c1, c2, c3, c4, c5 = st.columns(5)
    for c, label, value in [
        (c1, "Total Projects", f"{total_projects:,}"),
        (c2, "Total Capacity (MW)", f"{total_capacity:,}"),
        (c3, "Avg Capacity / Project", f"{avg_capacity}"),
        (c4, "Active Checkpoints", f"{unique_checkpoints}"),
        (c5, "Active Milestones", f"{unique_milestones}"),
    ]:
        with c:
            st.markdown(f"<div class='card'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>", unsafe_allow_html=True)

def render_dashboard_template(df: pd.DataFrame):
    if df.empty: return
    st.markdown("<h2 class='section-title'>Portfolio Dashboard</h2>", unsafe_allow_html=True)
    render_kpis(df)
    t1c1, t1c2 = st.columns(2)
    with t1c1:
        ts = df.copy()
        ts["Month"] = pd.to_datetime(ts["Milestone_Start_Date"]).dt.to_period("M").dt.to_timestamp()
        ts_agg = ts.groupby("Month", as_index=False)["Project_ID"].count().rename(columns={"Project_ID":"Projects"})
        fig = px.line(ts_agg, x="Month", y="Projects", markers=True, title="Projects over time")
        st.plotly_chart(fig, use_container_width=True)
    with t1c2:
        dev_counts = df["Developer"].value_counts().reset_index()
        dev_counts.columns = ["Developer", "Projects"]
        fig = px.bar(dev_counts, x="Developer", y="Projects", title="Projects by developer")
        st.plotly_chart(fig, use_container_width=True)
    b1c1, b1c2 = st.columns(2)
    with b1c1:
        cap_state = df.groupby("State", as_index=False)["Capacity_MW"].sum()
        fig = px.bar(cap_state, x="State", y="Capacity_MW", title="Capacity by state")
        st.plotly_chart(fig, use_container_width=True)
    with b1c2:
        share = df["State"].value_counts().reset_index()
        share.columns = ["State", "Projects"]
        fig = px.pie(share, names="State", values="Projects", hole=0.45, title="Projects share by state")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------
# PAGE
# ---------------------------------
if not milestones_df.empty and not projects_df.empty and CHECKPOINT_ORDER:
    # 1) Checkpoints single line
    st.markdown("<h2 class='subheader'>Project Process Workflow</h2>", unsafe_allow_html=True)
    cols = st.columns(len(CHECKPOINT_ORDER))
    for i, cp in enumerate(CHECKPOINT_ORDER, start=1):
        count = int(projects_df[projects_df["Checkpoint"] == cp].shape[0])
        label = f"{i}. {cp}\n{count} projects"
        with cols[i-1]:
            if st.button(label, key=f"cp_btn_{i}", use_container_width=True):
                if st.session_state.selected_checkpoint == cp:
                    st.session_state.selected_checkpoint = None
                    st.session_state.selected_milestone = None
                else:
                    st.session_state.selected_checkpoint = cp
                    st.session_state.selected_milestone = None

    # 2) Milestones grid (toggle) under selected checkpoint
    if st.session_state.selected_checkpoint:
        render_milestones_grid(st.session_state.selected_checkpoint, cols_per_row=4)

    # 3) India map
    render_state_bubble_map(projects_df)

    # add spacing before dashboard
    st.markdown("<br><br>", unsafe_allow_html=True)

    # 4) Filter for dashboard + optional table
    current_df = projects_df.copy()
    if st.session_state.get("selected_checkpoint"):
        current_df = current_df[current_df["Checkpoint"] == st.session_state.selected_checkpoint]
    if st.session_state.get("selected_milestone"):
        current_df = current_df[current_df["Milestone"] == st.session_state.selected_milestone]
        st.dataframe(
            current_df[["Project_ID","Project_Name","Developer","Capacity_MW","State","Checkpoint","Milestone","Milestone_Start_Date"]]
            .reset_index(drop=True)
        )

    # 5) Tableau-like dashboard
    render_dashboard_template(current_df)
else:
    st.info("Place 'Milestones in RE projects.xlsx' in the app folder to see checkpoints, milestones, projects and dashboards.")
