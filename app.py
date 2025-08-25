# app.py
import streamlit as st
import pandas as pd
import random
import math

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
# Global Styles (animated background + lifted title + button styles)
# ----------------------------
st.markdown("""
<style>
/* ===== Animated, professional background ===== */
html, body, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 700px at 12% -10%, #F3FAF6 0%, transparent 60%),
    radial-gradient(1200px 700px at 90% 0%, #E8F3EE 0%, transparent 65%),
    linear-gradient(180deg, #FFFFFF 0%, #F7FBF9 100%);
}
[data-testid="stAppViewContainer"]::before {
  content:""; position: fixed; inset: 0; pointer-events: none; z-index: -2;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' opacity='0.05' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.7' numOctaves='3'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: cover;
}
[data-testid="stAppViewContainer"]::after {
  content:""; position: fixed; inset: -20% -10% -10% -10%; pointer-events: none; z-index: -1;
  background:
    radial-gradient(400px 300px at 15% 10%, rgba(30,106,84,0.12), transparent 60%),
    radial-gradient(500px 350px at 85% 20%, rgba(20,80,65,0.10), transparent 65%),
    radial-gradient(600px 400px at 50% 110%, rgba(8,54,45,0.08), transparent 70%);
  animation: floatGrad 18s ease-in-out infinite alternate;
}
@keyframes floatGrad {
  0%   { transform: translateY(0px) translateX(0px);   filter: hue-rotate(0deg);   }
  100% { transform: translateY(-12px) translateX(6px); filter: hue-rotate(-10deg); }
}

.stApp { font-family: 'Poppins', sans-serif; }

/* ===== Title ===== */
.main-title{
  font-size: 40px !important;
  font-weight: 800 !important;
  color: #0F4237 !important;
  text-align: center;
  margin-top: 6px;
  margin-bottom: 8px;
  text-shadow: 0 1px 0 rgba(255,255,255,0.7);
}

/* Section title */
.subheader, .section-title {
  font-size: 26px !important;
  font-weight: 700 !important;
  color: #1b5e20 !important;
  margin-top: 20px;
  margin-bottom: 14px;
  text-align: center;
}

/* General button (checkpoint/milestone buttons) */
div.stButton > button {
  border-radius: 12px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  padding: 12px 14px !important;
  background-color: #f9f9f9 !important;
  border: 2px solid #1b5e20 !important;
  color: #1b5e20 !important;
  box-shadow: 2px 2px 10px rgba(0,0,0,0.10);
  transition: all 0.18s ease-in-out;
  width: 100%;
}
div.stButton > button:hover {
  background-color: #1b5e20 !important;
  color: white !important;
  transform: translateY(-1px);
}

/* Contact cards */
.card {
  border-radius: 16px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e8ecef;
  box-shadow: 0 10px 22px rgba(16,40,32,0.06);
}
.mapbox {
  height: 220px; border-radius: 14px; border: 1px dashed #cfd8dc;
  display: flex; align-items: center; justify-content: center; color: #6b7b83;
  background: #f8faf9; margin-top: 10px;
}
</style>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ----------------------------
# Session state
# ----------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "selected_state" not in st.session_state:
    st.session_state.selected_state = None

# ----------------------------
# Header (title only) + simple navigation row
# ----------------------------
st.markdown("<h1 class='main-title'>Real Time Project Milestone Monitoring Dashboard</h1>", unsafe_allow_html=True)

nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("Home", use_container_width=True):
        st.session_state.page = "Home"
        st.session_state.pop("selected_checkpoint", None)
        st.session_state.pop("selected_milestone", None)
        st.session_state.selected_state = None
with nav2:
    if st.button("Register Your Project", use_container_width=True):
        st.session_state.page = "Register"
with nav3:
    if st.button("Contact Us", use_container_width=True):
        st.session_state.page = "Contact"

# ----------------------------
# Data: Milestones + Dummy Projects
# ----------------------------
CHECKPOINT_ORDER = [
    "Issuance of LOA (Project Allocation) / LOI",
    "Applied for connectivity (NSWS)",
    "Conn BG 1/2",
    "Conn BG 3/4",
    "FTC (Grid India/NLDC/RLDC)"
]

@st.cache_data
def load_milestones_clean():
    df = pd.read_excel("Milestones in RE projects.xlsx", sheet_name="Sheet1")
    df = df.rename(columns={"Step No": "Step_No", "Checkpoints": "Checkpoint", "Milestones": "Milestone"})
    df = df.dropna(how="all")
    for c in ["Checkpoint", "Milestone"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["Checkpoint"] = df["Checkpoint"].replace({"nan": pd.NA}).ffill()
    is_loa_cp = df["Checkpoint"] == "Issuance of LOA (Project Allocation) / LOI"
    df.loc[is_loa_cp & (df["Milestone"].isna() | (df["Milestone"].str.len()==0) | (df["Milestone"].str.lower()=="nan")), "Milestone"] = "LoA"
    df = df[~df["Milestone"].isna()]
    df = df[df["Milestone"].str.len() > 0]
    df = df[df["Milestone"].str.lower() != "nan"]
    df = df[df["Checkpoint"].isin(CHECKPOINT_ORDER)]
    if "Step_No" in df.columns:
        df = df.sort_values("Step_No")
    return df.reset_index(drop=True)

try:
    milestones_df = load_milestones_clean()
except Exception as e:
    milestones_df = pd.DataFrame()
    st.error(f"Could not load 'Milestones in RE projects.xlsx' — {e}")

@st.cache_data
def generate_projects(n=900, mdf: pd.DataFrame = None):
    developers = ["Adani Green", "ReNew Power", "Tata Power", "Azure", "NTPC RE"]
    # Five demo states; add more if you like (and update STATE_CENTROIDS below)
    states = ["Rajasthan", "Gujarat", "Maharashtra", "Karnataka", "Tamil Nadu"]
    if mdf is None or mdf.empty:
        return pd.DataFrame()
    valid_rows = mdf[mdf["Milestone"].notna() & (mdf["Milestone"].str.len() > 0)]
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
            "Status": random.choice(["Not Started", "In Progress", "Completed"])
        })
    return pd.DataFrame(projects)

projects_df = generate_projects(900, milestones_df) if not milestones_df.empty else pd.DataFrame()

# ----------------------------
# Folium bubble map (no external files)
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
        st.info("No data to map yet.")
        return

    # Aggregate per state
    agg = df.groupby("State", as_index=False).agg(
        Projects=("Project_ID", "count"),
        Capacity_MW=("Capacity_MW", "sum"),
    )

    # Build map
    m = folium.Map(location=[22.97, 78.65], zoom_start=5, tiles="cartodbpositron")

    max_projects = max(agg["Projects"]) if not agg.empty else 1
    for state, (lat, lon) in STATE_CENTROIDS.items():
        row = agg[agg["State"] == state]
        projects = int(row["Projects"].iloc[0]) if not row.empty else 0
        capacity = int(row["Capacity_MW"].iloc[0]) if not row.empty else 0
        radius = 15 + (projects / max_projects) * 35 if max_projects > 0 else 15

        popup_html = f"<b>{state}</b><br>Projects: {projects}<br>Capacity: {capacity} MW"
        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            color="#1E6A54",
            fill=True,
            fill_color="#1E6A54",
            fill_opacity=0.65,
            tooltip=f"{state} — {projects} projects",
            popup=folium.Popup(popup_html, max_width=260)
        ).add_to(m)

    out = st_folium(m, width=None, height=520)
    # Detect click near a centroid to select a state
    if out and "last_object_clicked" in out and out["last_object_clicked"]:
        lat = out["last_object_clicked"]["lat"]
        lon = out["last_object_clicked"]["lng"]
        nearest_state = None
        nearest_dist = 9999
        for state, (slat, slon) in STATE_CENTROIDS.items():
            d = haversine_distance(lat, lon, slat, slon)
            if d < nearest_dist:
                nearest_dist = d
                nearest_state = state
        # If click within ~150km of a centroid, treat it as a state selection
        if nearest_state and nearest_dist < 150:
            st.session_state.selected_state = nearest_state

    # Show label for selected state
    if st.session_state.selected_state:
        sel = st.session_state.selected_state
        row = agg[agg["State"] == sel]
        total_p = int(row["Projects"].iloc[0]) if not row.empty else 0
        total_c = int(row["Capacity_MW"].iloc[0]) if not row.empty else 0
        st.success(f"📍 **{sel}** — Projects: **{total_p}**, Capacity: **{total_c} MW**")
    else:
        st.info("Tip: Click a state bubble to filter charts below.")

# ----------------------------
# Plotly dashboard (interactive)
# ----------------------------
def render_dashboard(df: pd.DataFrame, title: str):
    st.markdown(f"<h2 class='section-title'>{title}</h2>", unsafe_allow_html=True)
    if df.empty:
        st.info("No data to visualize yet.")
        return

    status_counts = df["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Projects"]
    st.plotly_chart(px.bar(status_counts, x="Status", y="Projects", title="Status distribution"), use_container_width=True)

    cap_by_state = df.groupby("State", as_index=False)["Capacity_MW"].sum().sort_values("Capacity_MW", ascending=False)
    st.plotly_chart(px.bar(cap_by_state, x="State", y="Capacity_MW", title="Total capacity by state (MW)"), use_container_width=True)

    dev_counts = df["Developer"].value_counts().reset_index()
    dev_counts.columns = ["Developer", "Projects"]
    fig3 = px.bar(dev_counts.head(10), x="Projects", y="Developer", orientation="h", title="Projects by developer (top)")
    fig3.update_layout(yaxis={"categoryorder":"total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

    ms_counts = df["Milestone"].value_counts().reset_index()
    ms_counts.columns = ["Milestone", "Projects"]
    st.plotly_chart(px.bar(ms_counts, x="Milestone", y="Projects", title="Projects by milestone"), use_container_width=True)

# ----------------------------
# Enhanced Contact
# ----------------------------
def render_contact_enhanced():
    st.markdown("<h1 class='main-title'>Contact Us</h1>", unsafe_allow_html=True)
    left, right = st.columns([1.15, 0.85], vertical_alignment="top")
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Get in touch")
        st.markdown("Tell us about your project. We’ll get back within 1 business day.")
        with st.form("contact_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Full name*")
                email = st.text_input("Work email*")
            with c2:
                org = st.text_input("Organization / Company")
                phone = st.text_input("Phone (optional)")
            message = st.text_area("Your message*", height=140)
            send = st.form_submit_button("Send message")
            if send:
                if name and email and message:
                    st.success("✅ Thanks! We’ll be in touch shortly.")
                else:
                    st.error("Please fill in name, email, and message.")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### NSEFI Headquarters")
        st.write("National Solar Energy Federation of India (NSEFI)")
        st.write("New Delhi, India")
        st.markdown('<div class="mapbox">Map placeholder (embed map/iframe here)</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------
# Pages
# ----------------------------
if st.session_state.page == "Home":
    st.markdown("<h2 class='subheader'>Project Roadmap</h2>", unsafe_allow_html=True)

    if milestones_df.empty or projects_df.empty:
        st.info("Place 'Milestones in RE projects.xlsx' in the app folder to see checkpoints, milestones and projects.")
    else:
        # 1) Checkpoints
        cols = st.columns(len(CHECKPOINT_ORDER))
        for i, cp in enumerate(CHECKPOINT_ORDER):
            count = projects_df[projects_df["Checkpoint"] == cp].shape[0]
            with cols[i]:
                if st.button(f"{cp}\n({count} projects)", key=f"cp_{i}"):
                    st.session_state.selected_checkpoint = cp
                    st.session_state.pop("selected_milestone", None)
                    st.session_state.selected_state = None

        # 2) Milestones for selected checkpoint
        if "selected_checkpoint" in st.session_state:
            cp = st.session_state.selected_checkpoint
            st.markdown(f"<h2 class='subheader'>Milestones in {cp}</h2>", unsafe_allow_html=True)
            ms_list = (
                milestones_df.loc[milestones_df["Checkpoint"] == cp, "Milestone"]
                .dropna().astype(str).str.strip().replace({"nan": ""})
            )
            ms_unique = [m for m in ms_list.unique().tolist() if m]
            if len(ms_unique) > 0:
                cols = st.columns(min(len(ms_unique), 4))
                for j, m in enumerate(ms_unique):
                    count = projects_df[projects_df["Milestone"] == m].shape[0]
                    col = cols[j % len(cols)]
                    with col:
                        if st.button(f"{m}\n({count} projects)", key=f"ms_{j}"):
                            st.session_state.selected_milestone = m
                            st.session_state.selected_state = None
            else:
                st.info("⚠️ No milestones defined for this checkpoint in the Excel.")

        # 3) India map directly under checkpoints
        render_state_bubble_map(projects_df)

        # 4) Projects table when a milestone is selected
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
            st.dataframe(current_df.reset_index(drop=True))

        if st.session_state.get("selected_state"):
            current_df = current_df[current_df["State"] == st.session_state.selected_state]
            dash_title += f" — {st.session_state.selected_state}"

        # 5) Interactive charts below (filtered by selections)
        render_dashboard(current_df, dash_title)

elif st.session_state.page == "Register":
    st.markdown("<h1 class='main-title'>Register Your Project</h1>", unsafe_allow_html=True)

    if not st.session_state.logged_in:
        with st.form("login_form"):
            st.write("🔑 Login to manage existing projects")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            if login_btn:
                if username and password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success(f"Welcome, {username}! You are now logged in.")
                else:
                    st.error("Please enter both username and password")

    if st.session_state.logged_in:
        st.success(f"Hello {st.session_state.username}, here are your projects:")
        if not projects_df.empty:
            st.dataframe(projects_df.sample(min(5, len(projects_df))))  # demo only
        else:
            st.info("No sample projects to display yet.")

    st.markdown("### Or Register a New Project")
    with st.form("project_form"):
        project_name = st.text_input("Project Name")
        developer = st.text_input("Developer Name")
        capacity = st.number_input("Capacity (MW)", min_value=10, max_value=1000, step=10)
        state = st.text_input("State")
        upload = st.file_uploader("Upload Supporting Documents", type=["pdf", "docx", "xlsx"])
        submit = st.form_submit_button("Register Project")
        if submit:
            st.success(f"✅ Project '{project_name}' registered successfully!")

elif st.session_state.page == "Contact":
    render_contact_enhanced()
