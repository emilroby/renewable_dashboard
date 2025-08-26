# app.py
import streamlit as st
import pandas as pd
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

# Interactive viz
import plotly.express as px
from streamlit_folium import st_folium
import folium

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(
    page_title="Real Time Project Milestone Monitoring Dashboard",
    layout="wide"
)

# ----------------------------
# Global Styles
# ----------------------------
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
  font-size: 40px !important;
  font-weight: 800 !important;
  color: #0F4237 !important;
  text-align: center;
  margin-top: 6px;
  margin-bottom: 8px;
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

/* Big cards as buttons (text wraps nicely) */
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

/* Simple card (container style) */
.card {
  border-radius: 16px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e8ecef;
  box-shadow: 0 10px 22px rgba(16,40,32,0.06);
}
</style>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ----------------------------
# Session state
# ----------------------------
if "selected_state" not in st.session_state:
    st.session_state.selected_state = None
if "selected_checkpoint" not in st.session_state:
    st.session_state.selected_checkpoint = None
if "selected_milestone" not in st.session_state:
    st.session_state.selected_milestone = None

# ----------------------------
# Robust logo finder (handles case/path differences)
# ----------------------------
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

MNRE_LOGO = find_logo(["MNRE.png", "mnre.png", "MNRE.PNG"])
NSEFI_LOGO = find_logo(["12th_year_anniversary_logo_transparent.png",
                        "12th_year_anniversary_logo_transparent.PNG"])

# ----------------------------
# Header row (MNRE left • Title center • NSEFI right)
# ----------------------------
top_left, top_mid, top_right = st.columns([1, 6, 1])
with top_left:
    if MNRE_LOGO:
        st.image(MNRE_LOGO, width=120)
    else:
        st.caption(" ")
with top_mid:
    st.markdown("<h1 class='main-title'>Real Time Project Milestone Monitoring Dashboard</h1>", unsafe_allow_html=True)
with top_right:
    if NSEFI_LOGO:
        st.image(NSEFI_LOGO, width=140)
    else:
        st.caption(" ")

# ----------------------------
# Data: Milestones (dynamic) + Dummy Projects
# ----------------------------
FILE_PATH = "Milestones in RE projects.xlsx"
FILE_MTIME = Path(FILE_PATH).stat().st_mtime if Path(FILE_PATH).exists() else 0

@st.cache_data
def load_milestones_clean(file_path: str, file_mtime: float):
    """Load and clean milestones; cache invalidates when file mtime changes."""
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df = df.rename(columns={"Step No": "Step_No", "Checkpoints": "Checkpoint", "Milestones": "Milestone"})
    df = df.dropna(how="all")

    # Trim & clean
    for c in ["Checkpoint", "Milestone"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["Checkpoint"] = df["Checkpoint"].replace({"nan": pd.NA}).ffill()

    # Fill blank milestone under LOA row as "LoA" (common pattern)
    is_loa_cp = df["Checkpoint"] == "Issuance of LOA (Project Allocation) / LOI"
    df.loc[is_loa_cp & (df["Milestone"].isna() | (df["Milestone"].str.len()==0) | (df["Milestone"].str.lower()=="nan")), "Milestone"] = "LoA"

    # Remove empties
    df = df[~df["Milestone"].isna()]
    df = df[df["Milestone"].str.len() > 0]
    df = df[df["Milestone"].str.lower() != "nan"]

    # Sort by step if available
    if "Step_No" in df.columns:
        df = df.sort_values("Step_No")

    return df.reset_index(drop=True)

if Path(FILE_PATH).exists():
    try:
        milestones_df = load_milestones_clean(FILE_PATH, FILE_MTIME)
    except Exception as e:
        milestones_df = pd.DataFrame()
        st.error(f"Could not load '{FILE_PATH}' — {e}")
else:
    milestones_df = pd.DataFrame()
    st.warning(f"'{FILE_PATH}' not found in the app folder.")

# Build CHECKPOINT_ORDER dynamically from Excel (first occurrence order by Step_No)
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

# Optional: quick cache-buster while iterating
cols_reload = st.columns([1,6,1])
with cols_reload[0]:
    if st.button("🔄 Force reload milestones"):
        st.cache_data.clear()
        st.rerun()

# ----------------------------
# Checkpoints row (single line, numbered 1..N)
# ----------------------------
def render_checkpoints_row():
    st.markdown("<h2 class='subheader'>Project Process Workflow</h2>", unsafe_allow_html=True)
    cps = CHECKPOINT_ORDER
    if not cps:
        return
    cols = st.columns(len(cps))
    for i, cp in enumerate(cps, start=1):
        count = int(projects_df[projects_df["Checkpoint"] == cp].shape[0])
        label = f"{i}. {cp}\n{count} projects"
        with cols[i-1]:
            if st.button(label, key=f"cp_btn_{i}", use_container_width=True):
                # Toggle: clicking same cp collapses milestones
                if st.session_state.selected_checkpoint == cp:
                    st.session_state.selected_checkpoint = None
                    st.session_state.selected_milestone = None
                else:
                    st.session_state.selected_checkpoint = cp
                    st.session_state.selected_milestone = None

# ----------------------------
# Milestones grid (horizontal wrapping; numbered X.1, X.2..., no arrows)
# ----------------------------
def render_milestones_grid(cp: str, cols_per_row: int = 4):
    if not cp:
        return
    cp_index = CHECKPOINT_ORDER.index(cp) + 1
    ms_series = (
        milestones_df.loc[milestones_df["Checkpoint"] == cp, "Milestone"]
        .dropna().astype(str).str.strip().replace({"nan": ""})
    )
    ms_unique = [m for m in ms_series.unique().tolist() if m]
    if not ms_unique:
        st.info("⚠️ No milestones defined for this checkpoint in the Excel.")
        return

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
                    # Toggle: clicking same milestone unselects
                    st.session_state.selected_milestone = (None if st.session_state.selected_milestone == m else m)
            j += 1

# ----------------------------
# India bubble map (capacity-scaled)
# ----------------------------
STATE_CENTROIDS = {
    "Rajasthan":  (27.0238, 74.2179),
    "Gujarat":    (22.2587, 71.1924),
    "Maharashtra":(19.7515, 75.7139),
    "Karnataka":  (15.3173, 75.7139),
    "Tamil Nadu": (11.1271, 78.6569),
}

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlambda = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2*math.atan2(math.sqrt(a), math.sqrt(1-a)))

def render_state_bubble_map(df: pd.DataFrame):
    st.markdown("<h2 class='section-title'>India — Projects by State</h2>", unsafe_allow_html=True)
    if df.empty:
        return
    agg = df.groupby("State", as_index=False).agg(
        Projects=("Project_ID", "count"),
        Capacity_MW=("Capacity_MW", "sum"),
    )
    m = folium.Map(location=[22.97, 78.65], zoom_start=5, tiles="cartodbpositron")
    max_cap = max(agg["Capacity_MW"]) if not agg.empty else 1
    for state, (lat, lon) in STATE_CENTROIDS.items():
        row = agg[agg["State"] == state]
        projects = int(row["Projects"].iloc[0]) if not row.empty else 0
        capacity = int(row["Capacity_MW"].iloc[0]) if not row.empty else 0
        radius = 12 + (capacity / max_cap) * 38 if max_cap > 0 else 12
        popup_html = f"<b>{state}</b><br>Projects: {projects}<br>Capacity: {capacity} MW"
        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            color="#1E6A54",
            fill=True,
            fill_color="#1E6A54",
            fill_opacity=0.65,
            tooltip=f"{state} — {capacity} MW",
            popup=folium.Popup(popup_html, max_width=260)
        ).add_to(m)
    out = st_folium(m, width=None, height=520)
    if out and "last_object_clicked" in out and out["last_object_clicked"]:
        lat = out["last_object_clicked"]["lat"]
        lon = out["last_object_clicked"]["lng"]
        nearest_state, nearest_dist = None, 9999
        for s, (slat, slon) in STATE_CENTROIDS.items():
            d = haversine_distance(lat, lon, slat, slon)
            if d < nearest_dist:
                nearest_state, nearest_dist = s, d
        if nearest_state and nearest_dist < 150:
            st.session_state.selected_state = nearest_state
    if st.session_state.selected_state:
        sel = st.session_state.selected_state
        row = agg[agg["State"] == sel]
        total_p = int(row["Projects"].iloc[0]) if not row.empty else 0
        total_c = int(row["Capacity_MW"].iloc[0]) if not row.empty else 0
        st.success(f"📍 **{sel}** — Projects: **{total_p}**, Capacity: **{total_c} MW**")

# ----------------------------
# Charts & Table
# ----------------------------
def render_dashboard(df: pd.DataFrame, title: str):
    st.markdown(f"<h2 class='section-title'>{title}</h2>", unsafe_allow_html=True)
    if df.empty:
        return

    # Donut: Projects share by state
    share_state = df["State"].value_counts().reset_index()
    share_state.columns = ["State", "Projects"]
    fig1 = px.pie(share_state, names="State", values="Projects", hole=0.45, title="Projects share by state")
    st.plotly_chart(fig1, use_container_width=True)

    # Bar: Capacity by state
    cap_by_state = df.groupby("State", as_index=False)["Capacity_MW"].sum().sort_values("Capacity_MW", ascending=False)
    fig2 = px.bar(cap_by_state, x="State", y="Capacity_MW", title="Total capacity by state (MW)")
    st.plotly_chart(fig2, use_container_width=True)

    # Line: Projects over time (by milestone month)
    ts = df.copy()
    ts["Month"] = pd.to_datetime(ts["Milestone_Start_Date"]).dt.to_period("M").dt.to_timestamp()
    ts_agg = ts.groupby("Month", as_index=False)["Project_ID"].count().rename(columns={"Project_ID":"Projects"})
    fig3 = px.line(ts_agg, x="Month", y="Projects", markers=True, title="Projects reaching milestones over time (monthly)")
    st.plotly_chart(fig3, use_container_width=True)

    # Scatter: Capacity vs milestone date by state
    fig4 = px.scatter(df, x="Milestone_Start_Date", y="Capacity_MW",
                      color="State", hover_data=["Project_ID", "Milestone", "Checkpoint"],
                      title="Capacity vs milestone date by state")
    st.plotly_chart(fig4, use_container_width=True)

    # Bar: Projects by milestone
    ms_counts = df["Milestone"].value_counts().reset_index()
    ms_counts.columns = ["Milestone", "Projects"]
    fig5 = px.bar(ms_counts, x="Milestone", y="Projects", title="Projects by milestone")
    st.plotly_chart(fig5, use_container_width=True)

# ----------------------------
# ---- PAGE RENDER ----
# ----------------------------
if milestones_df.empty or projects_df.empty or not CHECKPOINT_ORDER:
    st.info("Add/update 'Milestones in RE projects.xlsx' (with Sheet1 & columns: Step No, Checkpoints, Milestones) to see checkpoints, milestones and projects.")
else:
    # 1) Checkpoints row (single line, numbered 1..N)
    render_checkpoints_row()

    # 2) Milestones grid under the selected checkpoint (toggle)
    if st.session_state.selected_checkpoint:
        render_milestones_grid(st.session_state.selected_checkpoint, cols_per_row=4)

    # 3) India map
    render_state_bubble_map(projects_df)

    # 4) Table + Charts (filtered by selections)
    current_df = projects_df.copy()
    dash_title = "Portfolio overview"
    if st.session_state.get("selected_checkpoint"):
        current_df = current_df[current_df["Checkpoint"] == st.session_state.selected_checkpoint]
        dash_title = f"Dashboard — {st.session_state.selected_checkpoint}"
    if st.session_state.get("selected_milestone"):
        current_df = current_df[current_df["Milestone"] == st.session_state.selected_milestone]
        dash_title = f"Dashboard — {st.session_state.selected_milestone}"
        st.markdown(f"<h2 class='subheader'>Projects at milestone: {st.session_state.selected_milestone}</h2>", unsafe_allow_html=True)
        st.metric("Total Projects", len(current_df))
        st.dataframe(
            current_df[["Project_ID","Project_Name","Developer","Capacity_MW","State","Checkpoint","Milestone","Milestone_Start_Date"]]
            .reset_index(drop=True)
        )
    if st.session_state.get("selected_state"):
        current_df = current_df[current_df["State"] == st.session_state.selected_state]
        dash_title += f" — {st.session_state.selected_state}"
    render_dashboard(current_df, dash_title)
