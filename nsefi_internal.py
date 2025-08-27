# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from urllib.parse import quote

# --------------------------- CONFIG ---------------------------
st.set_page_config(
    page_title="NSEFI Policy & Regulatory Monitoring Dashboard",
    layout="wide",
    page_icon="🟩",
)

TITLE = "NSEFI policy and regulatory monitoring dashboard"

CENTRAL_ENTITIES = ["MNRE", "MoP", "MoF", "CEA", "CERC", "CTUIL"]

STATES_AND_UTS = [
    # States (28)
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # UTs (8)
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

# --------------------------- UTILS ---------------------------
def get_query_params() -> dict:
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()

def qp(key: str, default: str = "") -> str:
    params = get_query_params()
    val = params.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val if isinstance(val, str) else default

def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    from io import BytesIO
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        writer.close()
    buffer.seek(0)
    return buffer.read()

def ensure_session():
    if "uploaded_tables" not in st.session_state:
        st.session_state.uploaded_tables = {}  # key: (page, level, entity) -> DataFrame
    if "home_news_df" not in st.session_state:
        st.session_state.home_news_df = default_news_df()

def default_news_df():
    data = [
        {"state": "Andhra Pradesh", "date": datetime.today().strftime("%Y-%m-%d"),
         "update": "APERC invites comments on draft amendments to RE tariff order.", "link": ""},
        {"state": "Gujarat", "date": datetime.today().strftime("%Y-%m-%d"),
         "update": "GUVNL announces new solar tender for agri feeders.", "link": ""},
        {"state": "Tamil Nadu", "date": datetime.today().strftime("%Y-%m-%d"),
         "update": "TNERC consults on rooftop net metering clarifications.", "link": ""},
        {"state": "Maharashtra", "date": datetime.today().strftime("%Y-%m-%d"),
         "update": "MERC proposes TOU tariffs; hearing scheduled.", "link": ""},
        {"state": "Rajasthan", "date": datetime.today().strftime("%Y-%m-%d"),
         "update": "RRECL issues draft RE policy update for feedback.", "link": ""},
        {"state": "Telangana", "date": datetime.today().strftime("%Y-%m-%d"),
         "update": "TSREDCO updates empanelment for rooftop vendors.", "link": ""},
    ]
    return pd.DataFrame(data, columns=["state", "date", "update", "link"])

# --------------------------- STYLES ---------------------------
def css() -> str:
    return """
<style>
.block-container { padding-top: 1rem; }

/* Title spacing */
h1#title { margin-bottom: 0.6rem; }

/* Ribbon / Navbar */
.navwrap {
  position: sticky; top: 0; z-index: 9999;
}
.navbar {
  width: 100%;
  background: #1E6A54;
  border-radius: 10px;
  padding: 0; margin: 0 0 1rem 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  overflow: visible;
}
.navbar ul { list-style: none; margin: 0; padding: 0; display: flex; }
.navbar > ul > li { position: relative; }
.navbar a, .navbar span {
  display: block; padding: 12px 16px; color: #fff; text-decoration: none;
  font-weight: 600; font-size: 15px; white-space: nowrap;
}
.navbar > ul > li:hover { background: #195E4B; cursor: pointer; }

/* Dropdown level 1 */
.navbar ul li .dropdown {
  display: none; position: absolute; background: #195E4B; min-width: 180px; top: 100%; left: 0;
  border-radius: 0 0 10px 10px; overflow: hidden; box-shadow: 0 6px 16px rgba(0,0,0,0.2);
  flex-direction: column;
}
.navbar ul li:hover > .dropdown { display: block; }
.dropdown li { position: relative; }
.dropdown li:hover { background: #144F41; }

/* Flyout level 2 (side box) */
.dropdown .flyout {
  display: none; position: absolute; top: 0; left: 100%; min-width: 240px; max-height: 420px; overflow: auto;
  background: #144F41; border-radius: 0 10px 10px 10px; box-shadow: 0 6px 16px rgba(0,0,0,0.25);
}
.dropdown li:hover > .flyout { display: block; }

/* Home state cards */
.state-card {
  border: 1px solid #E7E7E7; border-radius: 12px; padding: 12px; height: 100%;
  background: #FCFAF0; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.state-card .state { font-weight: 700; margin-bottom: 6px; color: #1E6A54; }
.state-card .date { font-size: 12px; opacity: 0.8; margin-bottom: 6px; }
.state-card .update { font-size: 14px; line-height: 1.35; }

/* Optional: hide Streamlit chrome for internal-tool look */
header[data-testid="stHeader"] { background: rgba(0,0,0,0); }
footer { visibility: hidden; }
</style>
"""

# --------------------------- NAVBAR (WITH YOUR EXACT HTML) ---------------------------
def navbar_html() -> str:
    # Home tab (simple)
    home_link = '<li><a href="?page=home">Home</a></li>'

    # Your exact dropdown markup (unchanged, just wrapped)
    reps = r'''
<li>
  <span>Representations</span>
  <ul class="dropdown">
    <li><span>Central ▸</span><ul class="flyout"><li><a href="?page=representations&level=central&entity=MNRE">MNRE</a></li><li><a href="?page=representations&level=central&entity=MoP">MoP</a></li><li><a href="?page=representations&level=central&entity=MoF">MoF</a></li><li><a href="?page=representations&level=central&entity=CEA">CEA</a></li><li><a href="?page=representations&level=central&entity=CERC">CERC</a></li><li><a href="?page=representations&level=central&entity=CTUIL">CTUIL</a></li></ul></li>
    <li><span>State ▸</span><ul class="flyout" style="min-width:280px"><li><a href="?page=representations&level=state&entity=Andhra%20Pradesh">Andhra Pradesh</a></li><li><a href="?page=representations&level=state&entity=Arunachal%20Pradesh">Arunachal Pradesh</a></li><li><a href="?page=representations&level=state&entity=Assam">Assam</a></li><li><a href="?page=representations&level=state&entity=Bihar">Bihar</a></li><li><a href="?page=representations&level=state&entity=Chhattisgarh">Chhattisgarh</a></li><li><a href="?page=representations&level=state&entity=Goa">Goa</a></li><li><a href="?page=representations&level=state&entity=Gujarat">Gujarat</a></li><li><a href="?page=representations&level=state&entity=Haryana">Haryana</a></li><li><a href="?page=representations&level=state&entity=Himachal%20Pradesh">Himachal Pradesh</a></li><li><a href="?page=representations&level=state&entity=Jharkhand">Jharkhand</a></li><li><a href="?page=representations&level=state&entity=Karnataka">Karnataka</a></li><li><a href="?page=representations&level=state&entity=Kerala">Kerala</a></li><li><a href="?page=representations&level=state&entity=Madhya%20Pradesh">Madhya Pradesh</a></li><li><a href="?page=representations&level=state&entity=Maharashtra">Maharashtra</a></li><li><a href="?page=representations&level=state&entity=Manipur">Manipur</a></li><li><a href="?page=representations&level=state&entity=Meghalaya">Meghalaya</a></li><li><a href="?page=representations&level=state&entity=Mizoram">Mizoram</a></li><li><a href="?page=representations&level=state&entity=Nagaland">Nagaland</a></li><li><a href="?page=representations&level=state&entity=Odisha">Odisha</a></li><li><a href="?page=representations&level=state&entity=Punjab">Punjab</a></li><li><a href="?page=representations&level=state&entity=Rajasthan">Rajasthan</a></li><li><a href="?page=representations&level=state&entity=Sikkim">Sikkim</a></li><li><a href="?page=representations&level=state&entity=Tamil%20Nadu">Tamil Nadu</a></li><li><a href="?page=representations&level=state&entity=Telangana">Telangana</a></li><li><a href="?page=representations&level=state&entity=Tripura">Tripura</a></li><li><a href="?page=representations&level=state&entity=Uttar%20Pradesh">Uttar Pradesh</a></li><li><a href="?page=representations&level=state&entity=Uttarakhand">Uttarakhand</a></li><li><a href="?page=representations&level=state&entity=West%20Bengal">West Bengal</a></li><li><a href="?page=representations&level=state&entity=Andaman%20and%20Nicobar%20Islands">Andaman and Nicobar Islands</a></li><li><a href="?page=representations&level=state&entity=Chandigarh">Chandigarh</a></li><li><a href="?page=representations&level=state&entity=Dadra%20and%20Nagar%20Haveli%20and%20Daman%20and%20Diu">Dadra and Nagar Haveli and Daman and Diu</a></li><li><a href="?page=representations&level=state&entity=Delhi">Delhi</a></li><li><a href="?page=representations&level=state&entity=Jammu%20and%20Kashmir">Jammu and Kashmir</a></li><li><a href="?page=representations&level=state&entity=Ladakh">Ladakh</a></li><li><a href="?page=representations&level=state&entity=Lakshadweep">Lakshadweep</a></li><li><a href="?page=representations&level=state&entity=Puducherry">Puducherry</a></li></ul></li>
  </ul>
</li>
'''
    pols = r'''
<li>
  <span>Policies</span>
  <ul class="dropdown">
    <li><span>Central ▸</span><ul class="flyout"><li><a href="?page=policies&level=central&entity=MNRE">MNRE</a></li><li><a href="?page=policies&level=central&entity=MoP">MoP</a></li><li><a href="?page=policies&level=central&entity=MoF">MoF</a></li><li><a href="?page=policies&level=central&entity=CEA">CEA</a></li><li><a href="?page=policies&level=central&entity=CERC">CERC</a></li><li><a href="?page=policies&level=central&entity=CTUIL">CTUIL</a></li></ul></li>
    <li><span>State ▸</span><ul class="flyout" style="min-width:280px"><li><a href="?page=policies&level=state&entity=Andhra%20Pradesh">Andhra Pradesh</a></li><li><a href="?page=policies&level=state&entity=Arunachal%20Pradesh">Arunachal Pradesh</a></li><li><a href="?page=policies&level=state&entity=Assam">Assam</a></li><li><a href="?page=policies&level=state&entity=Bihar">Bihar</a></li><li><a href="?page=policies&level=state&entity=Chhattisgarh">Chhattisgarh</a></li><li><a href="?page=policies&level=state&entity=Goa">Goa</a></li><li><a href="?page=policies&level=state&entity=Gujarat">Gujarat</a></li><li><a href="?page=policies&level=state&entity=Haryana">Haryana</a></li><li><a href="?page=policies&level=state&entity=Himachal%20Pradesh">Himachal Pradesh</a></li><li><a href="?page=policies&level=state&entity=Jharkhand">Jharkhand</a></li><li><a href="?page=policies&level=state&entity=Karnataka">Karnataka</a></li><li><a href="?page=policies&level=state&entity=Kerala">Kerala</a></li><li><a href="?page=policies&level=state&entity=Madhya%20Pradesh">Madhya Pradesh</a></li><li><a href="?page=policies&level=state&entity=Maharashtra">Maharashtra</a></li><li><a href="?page=policies&level=state&entity=Manipur">Manipur</a></li><li><a href="?page=policies&level=state&entity=Meghalaya">Meghalaya</a></li><li><a href="?page=policies&level=state&entity=Mizoram">Mizoram</a></li><li><a href="?page=policies&level=state&entity=Nagaland">Nagaland</a></li><li><a href="?page=policies&level=state&entity=Odisha">Odisha</a></li><li><a href="?page=policies&level=state&entity=Punjab">Punjab</a></li><li><a href="?page=policies&level=state&entity=Rajasthan">Rajasthan</a></li><li><a href="?page=policies&level=state&entity=Sikkim">Sikkim</a></li><li><a href="?page=policies&level=state&entity=Tamil%20Nadu">Tamil Nadu</a></li><li><a href="?page=policies&level=state&entity=Telangana">Telangana</a></li><li><a href="?page=policies&level=state&entity=Tripura">Tripura</a></li><li><a href="?page=policies&level=state&entity=Uttar%20Pradesh">Uttar Pradesh</a></li><li><a href="?page=policies&level=state&entity=Uttarakhand">Uttarakhand</a></li><li><a href="?page=policies&level=state&entity=West%20Bengal">West Bengal</a></li><li><a href="?page=policies&level=state&entity=Andaman%20and%20Nicobar%20Islands">Andaman and Nicobar Islands</a></li><li><a href="?page=policies&level=state&entity=Chandigarh">Chandigarh</a></li><li><a href="?page=policies&level=state&entity=Dadra%20and%20Nagar%20Haveli%20and%20Daman%20and%20Diu">Dadra and Nagar Haveli and Daman and Diu</a></li><li><a href="?page=policies&level=state&entity=Delhi">Delhi</a></li><li><a href="?page=policies&level=state&entity=Jammu%20and%20Kashmir">Jammu and Kashmir</a></li><li><a href="?page=policies&level=state&entity=Ladakh">Ladakh</a></li><li><a href="?page=policies&level=state&entity=Lakshadweep">Lakshadweep</a></li><li><a href="?page=policies&level=state&entity=Puducherry">Puducherry</a></li></ul></li>
  </ul>
</li>
'''
    regs = r'''
<li>
  <span>Regulations</span>
  <ul class="dropdown">
    <li><span>Central ▸</span><ul class="flyout"><li><a href="?page=regulations&level=central&entity=MNRE">MNRE</a></li><li><a href="?page=regulations&level=central&entity=MoP">MoP</a></li><li><a href="?page=regulations&level=central&entity=MoF">MoF</a></li><li><a href="?page=regulations&level=central&entity=CEA">CEA</a></li><li><a href="?page=regulations&level=central&entity=CERC">CERC</a></li><li><a href="?page=regulations&level=central&entity=CTUIL">CTUIL</a></li></ul></li>
    <li><span>State ▸</span><ul class="flyout" style="min-width:280px"><li><a href="?page=regulations&level=state&entity=Andhra%20Pradesh">Andhra Pradesh</a></li><li><a href="?page=regulations&level=state&entity=Arunachal%20Pradesh">Arunachal Pradesh</a></li><li><a href="?page=regulations&level=state&entity=Assam">Assam</a></li><li><a href="?page=regulations&level=state&entity=Bihar">Bihar</a></li><li><a href="?page=regulations&level=state&entity=Chhattisgarh">Chhattisgarh</a></li><li><a href="?page=regulations&level=state&entity=Goa">Goa</a></li><li><a href="?page=regulations&level=state&entity=Gujarat">Gujarat</a></li><li><a href="?page=regulations&level=state&entity=Haryana">Haryana</a></li><li><a href="?page=regulations&level=state&entity=Himachal%20Pradesh">Himachal Pradesh</a></li><li><a href="?page=regulations&level=state&entity=Jharkhand">Jharkhand</a></li><li><a href="?page=regulations&level=state&entity=Karnataka">Karnataka</a></li><li><a href="?page=regulations&level=state&entity=Kerala">Kerala</a></li><li><a href="?page=regulations&level=state&entity=Madhya%20Pradesh">Madhya Pradesh</a></li><li><a href="?page=regulations&level=state&entity=Maharashtra">Maharashtra</a></li><li><a href="?page=regulations&level=state&entity=Manipur">Manipur</a></li><li><a href="?page=regulations&level=state&entity=Meghalaya">Meghalaya</a></li><li><a href="?page=regulations&level=state&entity=Mizoram">Mizoram</a></li><li><a href="?page=regulations&level=state&entity=Nagaland">Nagaland</a></li><li><a href="?page=regulations&level=state&entity=Odisha">Odisha</a></li><li><a href="?page=regulations&level=state&entity=Punjab">Punjab</a></li><li><a href="?page=regulations&level=state&entity=Rajasthan">Rajasthan</a></li><li><a href="?page=regulations&level=state&entity=Sikkim">Sikkim</a></li><li><a href="?page=regulations&level=state&entity=Tamil%20Nadu">Tamil Nadu</a></li><li><a href="?page=regulations&level=state&entity=Telangana">Telangana</a></li><li><a href="?page=regulations&level=state&entity=Tripura">Tripura</a></li><li><a href="?page=regulations&level=state&entity=Uttar%20Pradesh">Uttar Pradesh</a></li><li><a href="?page=regulations&level=state&entity=Uttarakhand">Uttarakhand</a></li><li><a href="?page=regulations&level=state&entity=West%20Bengal">West Bengal</a></li><li><a href="?page=regulations&level=state&entity=Andaman%20and%20Nicobar%20Islands">Andaman and Nicobar Islands</a></li><li><a href="?page=regulations&level=state&entity=Chandigarh">Chandigarh</a></li><li><a href="?page=regulations&level=state&entity=Dadra%20and%20Nagar%20Haveli%20and%20Daman%20and%20Diu">Dadra and Nagar Haveli and Daman and Diu</a></li><li><a href="?page=regulations&level=state&entity=Delhi">Delhi</a></li><li><a href="?page=regulations&level=state&entity=Jammu%20and%20Kashmir">Jammu and Kashmir</a></li><li><a href="?page=regulations&level=state&entity=Ladakh">Ladakh</a></li><li><a href="?page=regulations&level=state&entity=Lakshadweep">Lakshadweep</a></li><li><a href="?page=regulations&level=state&entity=Puducherry">Puducherry</a></li></ul></li>
  </ul>
</li>
'''
    return f'''
<div class="navwrap">
  <nav class="navbar">
    <ul>
      {home_link}
      {reps}
      {pols}
      {regs}
    </ul>
  </nav>
</div>
'''

# --------------------------- PAGES ---------------------------
def show_template_downloads():
    with st.expander("📥 Download CSV/XLSX templates"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Home: Latest News CSV**")
            st.caption("Columns: state, date (YYYY-MM-DD), update, link")
            st.download_button(
                "Download news_template.csv",
                default_news_df().to_csv(index=False).encode("utf-8"),
                "news_template.csv",
                "text/csv",
            )
        with c2:
            st.markdown("**Representations: Excel**")
            df = pd.DataFrame([
                {"date": "2025-08-01", "to": "MNRE", "subject": "Rooftop Subsidy",
                 "status": "Submitted", "notes": "Awaiting response"}
            ])
            st.download_button(
                "Download representations_template.xlsx",
                to_xlsx_bytes(df),
                "representations_template.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with c3:
            st.markdown("**Policies/Regulations: Excel**")
            dfp = pd.DataFrame([
                {"policy/regulation": "Andhra Pradesh RE Policy 2023",
                 "effective_from": "2023-06-01", "doc_link": "https://example.com"}
            ])
            st.download_button(
                "Download policy_regulation_template.xlsx",
                to_xlsx_bytes(dfp),
                "policy_regulation_template.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

def page_home():
    st.subheader("Latest updates by State/UT")
    st.caption("Upload a CSV to replace the starter dataset, or use the defaults shown below.")
    up = st.file_uploader("Upload latest updates CSV (state, date, update, link)", type=["csv"])
    if up is not None:
        try:
            df = pd.read_csv(up)
            needed = {"state", "date", "update", "link"}
            if not needed.issubset(set(df.columns)):
                st.error("CSV must have columns: state, date, update, link")
            else:
                st.session_state.home_news_df = df
                st.success("News updated from CSV.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    df = st.session_state.home_news_df.copy()
    df = df.sort_values("state")

    per_row = 4
    rows = [df.iloc[i:i+per_row] for i in range(0, len(df), per_row)]
    for chunk in rows:
        cols = st.columns(per_row)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                link_html = ""
                if str(row.get("link", "")).strip():
                    link_html = f"<div style='margin-top:6px'><a href='{row['link']}' target='_blank'>Open document</a></div>"
                st.markdown(
                    f"""
                    <div class="state-card">
                      <div class="state">{row['state']}</div>
                      <div class="date">Updated: {row['date']}</div>
                      <div class="update">{row['update']}</div>
                      {link_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    show_template_downloads()

def render_uploader_and_table(page: str, level: str, entity: str, note: str = ""):
    key = (page, level, entity)
    st.write(f"**Selection:** {page.title()} ➜ {level.title()} ➜ {entity}")
    if note:
        st.info(note)

    f = st.file_uploader(
        f"Upload {page.title()} data for '{entity}' (XLSX)",
        type=["xlsx"],
        key=f"uploader_{page}_{level}_{quote(entity)}",
    )
    if f is not None:
        try:
            df = pd.read_excel(f)
            st.session_state.uploaded_tables[key] = df
            st.success("File loaded.")
        except Exception as e:
            st.error(f"Could not read Excel: {e}")

    df = st.session_state.uploaded_tables.get(key)
    if df is not None and not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No data uploaded yet. Download a template below and upload your file.")
        show_template_downloads()

def page_representations(level: str, entity: str):
    if level == "central":
        if entity not in CENTRAL_ENTITIES:
            st.info("Choose a Central entity from the ribbon dropdown.")
            return
        render_uploader_and_table("representations", "central", entity)
    elif level == "state":
        if entity not in STATES_AND_UTS:
            st.info("Choose a State/UT from the ribbon dropdown.")
            return
        render_uploader_and_table("representations", "state", entity)
    else:
        st.info("Hover on ‘Representations’ in the ribbon → choose Central or State → select an item.")

def page_policies(level: str, entity: str):
    if level == "central":
        # Spec: show there is no national policy
        st.info("At the national (Central) level: there is no policy to display.")
        st.caption("Tip: Use the ‘State’ menu to view a specific state’s RE policy.")
    elif level == "state":
        if entity not in STATES_AND_UTS:
            st.info("Choose a State/UT from the ribbon dropdown.")
            return
        note = f"Showing **only** {entity} RE policy entries (upload your file below)."
        render_uploader_and_table("policies", "state", entity, note=note)
    else:
        st.info("Hover on ‘Policies’ in the ribbon → choose Central or State → select an item.")

def page_regulations(level: str, entity: str):
    if level == "central":
        if entity not in CENTRAL_ENTITIES:
            st.info("Choose a Central entity (CEA, CERC, etc.) from the ribbon dropdown.")
            return
        render_uploader_and_table("regulations", "central", entity)
    elif level == "state":
        if entity not in STATES_AND_UTS:
            st.info("Choose a State/UT from the ribbon dropdown.")
            return
        render_uploader_and_table("regulations", "state", entity)
    else:
        st.info("Hover on ‘Regulations’ in the ribbon → choose Central or State → select an item.")

# --------------------------- APP ENTRY ---------------------------
def main():
    ensure_session()

    # Title
    st.markdown(f'<h1 id="title">{TITLE}</h1>', unsafe_allow_html=True)

    # Styles + Navbar
    st.markdown(css(), unsafe_allow_html=True)
    st.markdown(navbar_html(), unsafe_allow_html=True)

    # Routing
    page = qp("page", "home").lower()
    level = qp("level", "").lower()
    entity = qp("entity", "")

    if page == "home":
        page_home()
    elif page == "representations":
        page_representations(level, entity)
    elif page == "policies":
        page_policies(level, entity)
    elif page == "regulations":
        page_regulations(level, entity)
    else:
        st.warning("Unknown page. Use the ribbon above to navigate.")

if __name__ == "__main__":
    main()
