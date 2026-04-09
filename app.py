import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# ─────────────────────────────────────────────
# PAGE CONFIG — must be first Streamlit command
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Helion GRC Dashboard",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #0f1117 0%, #1a1d2e 100%);
        border: 1px solid #2d3561;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    div[data-testid="metric-container"] label {
        color: #8892b0 !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #ccd6f6 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 1.8rem !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #0f1117;
        padding: 4px;
        border-radius: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 0.85rem;
        color: #8892b0;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2d3561 !important;
        color: #ccd6f6 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e1a 0%, #0f1117 100%);
        border-right: 1px solid #2d3561;
    }

    /* Dataframe */
    .stDataFrame {
        border: 1px solid #2d3561;
        border-radius: 8px;
    }

    /* Divider */
    hr {
        border-color: #2d3561 !important;
    }

    /* Section headers */
    .section-header {
        font-family: 'IBM Plex Mono', monospace;
        color: #64ffda;
        font-size: 0.75rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 1rem;
        border-left: 3px solid #64ffda;
        padding-left: 10px;
    }

    /* Status badges */
    .badge-implemented {
        background-color: #0d3d2e;
        color: #64ffda;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-partial {
        background-color: #3d2e0d;
        color: #ffd700;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-not {
        background-color: #3d0d0d;
        color: #ff6b6b;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────────

# PASTE YOUR SHEET ID HERE
SHEET_ID = "paste-your-sheet-id-here"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

@st.cache_data(ttl=300)
def load_all_data():
    """
    Loads all 7 sheets from Google Sheets.
    Cached for 5 minutes — auto-refreshes.
    All headers are at row 1, data starts at row 2.
    """
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SHEET_ID)

    def sheet_to_df(tab_name):
        """
        Reads a sheet where headers are in row 1.
        Removes completely empty rows.
        """
        try:
            worksheet = spreadsheet.worksheet(tab_name)
            data = worksheet.get_all_values()

            if len(data) < 2:
                st.warning(f"Sheet '{tab_name}' appears empty.")
                return pd.DataFrame()

            headers = data[0]       # Row 1 = headers
            rows    = data[1:]      # Row 2 onwards = data

            df = pd.DataFrame(rows, columns=headers)
            df = df.replace("", pd.NA).dropna(how="all")

            # Remove duplicate column names if any
            df = df.loc[:, ~df.columns.duplicated()]

            # Strip whitespace from all string values
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

            return df

        except Exception as e:
            st.error(f"Error loading sheet '{tab_name}': {e}")
            return pd.DataFrame()

    iso      = sheet_to_df("ISO27001_Compliance_Matrix")
    nist     = sheet_to_df("NIST_CSF_Profile")
    crosswalk= sheet_to_df("ISO-NIST_Crosswalk")
    roadmap  = sheet_to_df("Remediation_Roadmap")
    risk     = sheet_to_df("Risk_Register")
    soa      = sheet_to_df("Statement_of_Applicability")
    gdpr     = sheet_to_df("GDPR_Regulatory_Mapping")
    tprm_inv = sheet_to_df("TPRM_Vendor_Inventory")
    tprm_reg = sheet_to_df("TPRM_Vendor_Risk_Register")
    tprm_rem = sheet_to_df("TPRM_Remediation_Tracker")

    return iso, nist, crosswalk, roadmap, risk, soa, gdpr, tprm_inv, tprm_reg, tprm_rem


def to_numeric(df, columns):
    """Google Sheets returns everything as strings. Convert numeric columns."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── Load ──
with st.spinner("🔄 Connecting to Google Sheets..."):
    iso_df, nist_df, crosswalk_df, roadmap_df, risk_df, soa_df, gdpr_df, tprm_inv_df, tprm_reg_df, tprm_rem_df = load_all_data()

# ── Convert numeric columns using your exact column names ──
iso_df      = to_numeric(iso_df,  ["Risk Score"])
nist_df     = to_numeric(nist_df, ["Current Level", "Target Level", "Gap"])
risk_df     = to_numeric(risk_df, ["Likelihood", "Impact", "Inherent Risk", "Residual Risk"])

# ─────────────────────────────────────────────
# COLOUR MAPS  (reused across all charts)
# ─────────────────────────────────────────────
STATUS_COLORS = {
    "Implemented":     "#64ffda",
    "Partially":       "#ffd700",
    "Not Implemented": "#ff6b6b",
    "N/A":             "#4a5568"
}

RISK_COLORS = {
    "Critical": "#ff4444",
    "High":     "#ff8c00",
    "Medium":   "#ffd700",
    "Low":      "#64ffda"
}

PLOTLY_TEMPLATE = "plotly_dark"

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='text-align:center; padding: 10px 0 5px 0;'>
            <span style='font-size:2.5rem;'>🔐</span>
            <h2 style='color:#ccd6f6; margin:4px 0; font-family:"IBM Plex Mono",monospace;'>
                Helion GRC
            </h2>
            <p style='color:#64ffda; font-size:0.7rem; letter-spacing:0.15em;
                      text-transform:uppercase; margin:0;'>
                ISMS Dashboard
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("**🏢 Company Profile**")
    st.markdown("""
    - B2B SaaS — HR & Payroll
    - ~500 Employees
    - AWS Multi-Tenant
    - Remote-First, Global
    """)

    st.markdown("**📋 Frameworks**")
    st.markdown("""
    - ISO/IEC 27001:2022
    - NIST CSF 2.0
    - GDPR
    """)

    st.divider()

    st.markdown("**👤 Built by**")
    st.markdown("**Aryan Bhosale**")
    st.markdown("ISO 27001:2022 Lead Implementer")
    st.markdown("TÜV SÜD · GWU MS Cybersecurity")
    st.markdown("[LinkedIn ↗](https://linkedin.com/in/aryanbhosale23)")

    st.divider()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Data refreshes automatically every 5 min")

# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────
st.markdown("""
    <h1 style='font-family:"IBM Plex Mono",monospace; color:#ccd6f6;
               font-size:1.8rem; margin-bottom:0;'>
        🔐 Helion Technologies — GRC Dashboard
    </h1>
    <p style='color:#8892b0; font-size:0.85rem; margin-top:4px;'>
        ISO/IEC 27001:2022 &nbsp;·&nbsp; NIST CSF 2.0 &nbsp;·&nbsp; GDPR &nbsp;|&nbsp;
        Designed by <strong style='color:#64ffda;'>Aryan Bhosale</strong> &nbsp;·&nbsp;
        ISO 27001 Lead Implementer (TÜV SÜD)
    </p>
""", unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📊 Overview",
    "📋 ISO 27001 Matrix",
    "🎯 NIST CSF Profile",
    "🔗 ISO-NIST Crosswalk",
    "⚠️  Risk Register",
    "✅ Statement of Applicability",
    "🗺️  Remediation Roadmap",
    "🇪🇺 GDPR Mapping",
    "🏢 TPRM",
])

# ══════════════════════════════════════════════════════════
# TAB 1 ── OVERVIEW
# ══════════════════════════════════════════════════════════
with tab1:
    st.markdown('<p class="section-header">Program Overview</p>', unsafe_allow_html=True)

    # ── KPI row ──
    applicable_df = iso_df[iso_df["Applicable"].str.upper() == "YES"] if "Applicable" in iso_df.columns else iso_df
    total       = len(applicable_df)
    implemented = len(applicable_df[applicable_df["Status"] == "Implemented"])   if "Status" in applicable_df.columns else 0
    partial     = len(applicable_df[applicable_df["Status"] == "Partially"])     if "Status" in applicable_df.columns else 0
    not_impl    = len(applicable_df[applicable_df["Status"] == "Not Implemented"])if "Status" in applicable_df.columns else 0
    impl_rate   = round(implemented / total * 100, 1) if total > 0 else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Controls",      total)
    k2.metric("✅ Implemented",       implemented)
    k3.metric("🟡 Partially",         partial)
    k4.metric("🔴 Not Implemented",   not_impl)
    k5.metric("Implementation Rate",  f"{impl_rate}%")

    st.divider()

    col_left, col_right = st.columns(2)

    # Donut chart
    with col_left:
        st.markdown('<p class="section-header">Control Status Distribution</p>', unsafe_allow_html=True)
        if "Status" in iso_df.columns:
            sc = iso_df["Status"].value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig_donut = px.pie(
                sc, values="Count", names="Status",
                hole=0.58, color="Status",
                color_discrete_map=STATUS_COLORS,
                template=PLOTLY_TEMPLATE
            )
            fig_donut.update_traces(textposition="inside", textinfo="percent+label")
            fig_donut.update_layout(showlegend=False, margin=dict(t=20,b=20,l=20,r=20))
            st.plotly_chart(fig_donut, use_container_width=True)

    # Stacked bar by Domain
    with col_right:
        st.markdown('<p class="section-header">Controls by Domain & Status</p>', unsafe_allow_html=True)
        if all(c in iso_df.columns for c in ["Domain", "Status"]):
            ds = iso_df.groupby(["Domain","Status"]).size().reset_index(name="Count")
            fig_bar = px.bar(
                ds, x="Domain", y="Count", color="Status",
                color_discrete_map=STATUS_COLORS,
                barmode="stack", template=PLOTLY_TEMPLATE
            )
            fig_bar.update_layout(
                xaxis_title="", yaxis_title="Controls",
                legend_title="Status", margin=dict(t=20,b=60)
            )
            fig_bar.update_xaxes(tickangle=-30)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # Risk summary row
    st.markdown('<p class="section-header">Risk Posture at a Glance</p>', unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    if "Risk Level" in risk_df.columns:
        r1.metric("🔴 Critical", len(risk_df[risk_df["Risk Level"] == "Critical"]))
        r2.metric("🟠 High",     len(risk_df[risk_df["Risk Level"] == "High"]))
        r3.metric("🟡 Medium",   len(risk_df[risk_df["Risk Level"] == "Medium"]))
        r4.metric("🟢 Low",      len(risk_df[risk_df["Risk Level"] == "Low"]))

    st.divider()

    # NIST average maturity summary
    st.markdown('<p class="section-header">NIST CSF 2.0 — Maturity Snapshot</p>', unsafe_allow_html=True)
    if all(c in nist_df.columns for c in ["Current Level", "Target Level"]):
        avg_current = round(nist_df["Current Level"].mean(), 2)
        avg_target  = round(nist_df["Target Level"].mean(), 2)
        avg_gap     = round(avg_target - avg_current, 2)

        n1, n2, n3 = st.columns(3)
        n1.metric("Avg Current Maturity", f"{avg_current} / 4.0")
        n2.metric("Avg Target Maturity",  f"{avg_target} / 4.0")
        n3.metric("Avg Maturity Gap",     f"{avg_gap}")


# ══════════════════════════════════════════════════════════
# TAB 2 ── ISO 27001 COMPLIANCE MATRIX
# Columns: Control ID · Control Name · Domain · ISO Annex A Ref ·
#          NIST CSF Mapping · Applicable · Status · Owner ·
#          Evidence · Gap Description · Remediation Action ·
#          Priority · Risk Score
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown('<p class="section-header">ISO 27001:2022 Annex A — Control Matrix</p>', unsafe_allow_html=True)

    # Filters
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        domain_opts = iso_df["Domain"].dropna().unique().tolist() if "Domain" in iso_df.columns else []
        domain_filter = st.multiselect("Domain", options=domain_opts, default=domain_opts, key="iso_domain")

    with f2:
        status_opts = iso_df["Status"].dropna().unique().tolist() if "Status" in iso_df.columns else []
        status_filter = st.multiselect("Status", options=status_opts, default=status_opts, key="iso_status")

    with f3:
        priority_opts = iso_df["Priority"].dropna().unique().tolist() if "Priority" in iso_df.columns else []
        priority_filter = st.multiselect("Priority", options=priority_opts, default=priority_opts, key="iso_priority")

    with f4:
        app_filter = st.multiselect("Applicable", options=["YES","NO","Yes","No"], default=["YES","Yes"], key="iso_app")

    # Apply filters
    filtered_iso = iso_df.copy()
    if domain_filter   and "Domain"     in filtered_iso.columns: filtered_iso = filtered_iso[filtered_iso["Domain"].isin(domain_filter)]
    if status_filter   and "Status"     in filtered_iso.columns: filtered_iso = filtered_iso[filtered_iso["Status"].isin(status_filter)]
    if priority_filter and "Priority"   in filtered_iso.columns: filtered_iso = filtered_iso[filtered_iso["Priority"].isin(priority_filter)]
    if app_filter      and "Applicable" in filtered_iso.columns: filtered_iso = filtered_iso[filtered_iso["Applicable"].isin(app_filter)]

    # Colour status column
    def highlight_status(val):
        mapping = {
            "Implemented":     "background-color:#0d3d2e; color:#64ffda",
            "Partially":       "background-color:#3d2e0d; color:#ffd700",
            "Not Implemented": "background-color:#3d0d0d; color:#ff6b6b"
        }
        return mapping.get(val, "")

    display_cols = [c for c in [
        "Control ID","Control Name","Domain","ISO Annex A Ref",
        "NIST CSF Mapping","Applicable","Status","Owner",
        "Evidence","Gap Description","Remediation Action","Priority","Risk Score"
    ] if c in filtered_iso.columns]

    styled = filtered_iso[display_cols].style.applymap(
        highlight_status, subset=["Status"] if "Status" in display_cols else []
    )

    st.dataframe(styled, use_container_width=True, height=520)
    st.caption(f"Showing {len(filtered_iso)} of {len(iso_df)} controls")


# ══════════════════════════════════════════════════════════
# TAB 3 ── NIST CSF PROFILE
# Columns: Function · Category · Subcategory ID ·
#          Subcategory Description · Current Level · Target Level ·
#          Gap · Priority · Evidence · ISO 27001 Mapping
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown('<p class="section-header">NIST CSF 2.0 — Maturity Profile</p>', unsafe_allow_html=True)

    required_nist = ["Function","Current Level","Target Level"]
    if all(c in nist_df.columns for c in required_nist):

        nist_summary = nist_df.groupby("Function").agg(
            Current=("Current Level","mean"),
            Target =("Target Level","mean")
        ).reset_index()

        col_radar, col_gap = st.columns([3, 2])

        with col_radar:
            fns     = nist_summary["Function"].tolist()
            fns_c   = fns + [fns[0]]
            cur_c   = nist_summary["Current"].tolist() + [nist_summary["Current"].tolist()[0]]
            tgt_c   = nist_summary["Target"].tolist()  + [nist_summary["Target"].tolist()[0]]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=cur_c, theta=fns_c, fill="toself",
                name="Current Maturity",
                line_color="#ff6b6b",
                fillcolor="rgba(255,107,107,0.15)"
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=tgt_c, theta=fns_c, fill="toself",
                name="Target Maturity",
                line_color="#64ffda",
                fillcolor="rgba(100,255,218,0.08)"
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,4])),
                template=PLOTLY_TEMPLATE,
                title="Current vs Target Maturity by NIST Function",
                showlegend=True,
                legend=dict(x=0.8, y=1.1)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_gap:
            nist_summary["Gap"] = (nist_summary["Target"] - nist_summary["Current"]).round(2)
            fig_gap = px.bar(
                nist_summary.sort_values("Gap"),
                x="Gap", y="Function", orientation="h",
                color="Gap",
                color_continuous_scale=["#64ffda","#ffd700","#ff6b6b"],
                title="Maturity Gap (Target − Current)",
                template=PLOTLY_TEMPLATE
            )
            fig_gap.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_gap, use_container_width=True)

        st.divider()

        # Subcategory detail table with filter
        st.markdown('<p class="section-header">Subcategory Detail</p>', unsafe_allow_html=True)

        nf1, nf2 = st.columns(2)
        with nf1:
            fn_filter = st.selectbox(
                "Filter by NIST Function",
                options=["All"] + nist_df["Function"].dropna().unique().tolist()
            )
        with nf2:
            priority_nist = nist_df["Priority"].dropna().unique().tolist() if "Priority" in nist_df.columns else []
            nist_pri_filter = st.multiselect("Filter by Priority", options=priority_nist, default=priority_nist, key="nist_pri")

        filtered_nist = nist_df.copy()
        if fn_filter != "All":
            filtered_nist = filtered_nist[filtered_nist["Function"] == fn_filter]
        if nist_pri_filter and "Priority" in filtered_nist.columns:
            filtered_nist = filtered_nist[filtered_nist["Priority"].isin(nist_pri_filter)]

        st.dataframe(filtered_nist, use_container_width=True, height=400)

    else:
        st.warning("Column name mismatch. Expected: Function, Current Level, Target Level")


# ══════════════════════════════════════════════════════════
# TAB 4 ── ISO-NIST CROSSWALK
# Columns: Control ID · Control Name · Domain · ISO Annex A Ref ·
#          NIST CSF Subcategory(ies) · NIST Function(s) · Status · Notes
# ══════════════════════════════════════════════════════════
with tab4:
    st.markdown('<p class="section-header">ISO 27001 ↔ NIST CSF 2.0 Crosswalk</p>', unsafe_allow_html=True)

    st.info(
        "This crosswalk shows how each ISO 27001 Annex A control maps to NIST CSF 2.0 subcategories "
        "— enabling dual-framework coverage from a single control library. "
        "High-leverage controls appear in multiple NIST subcategories simultaneously.",
        icon="ℹ️"
    )

    # Filters
    cf1, cf2, cf3 = st.columns(3)

    with cf1:
        cw_domain_opts = crosswalk_df["Domain"].dropna().unique().tolist() if "Domain" in crosswalk_df.columns else []
        cw_domain_filter = st.multiselect("Domain", options=cw_domain_opts, default=cw_domain_opts, key="cw_domain")

    with cf2:
        cw_fn_opts = crosswalk_df["NIST Function(s)"].dropna().unique().tolist() if "NIST Function(s)" in crosswalk_df.columns else []
        cw_fn_filter = st.multiselect("NIST Function", options=cw_fn_opts, default=cw_fn_opts, key="cw_fn")

    with cf3:
        cw_status_opts = crosswalk_df["Status"].dropna().unique().tolist() if "Status" in crosswalk_df.columns else []
        cw_status_filter = st.multiselect("Status", options=cw_status_opts, default=cw_status_opts, key="cw_status")

    filtered_cw = crosswalk_df.copy()
    if cw_domain_filter  and "Domain"          in filtered_cw.columns: filtered_cw = filtered_cw[filtered_cw["Domain"].isin(cw_domain_filter)]
    if cw_fn_filter      and "NIST Function(s)" in filtered_cw.columns: filtered_cw = filtered_cw[filtered_cw["NIST Function(s)"].isin(cw_fn_filter)]
    if cw_status_filter  and "Status"           in filtered_cw.columns: filtered_cw = filtered_cw[filtered_cw["Status"].isin(cw_status_filter)]

    # Coverage chart — how many ISO controls map to each NIST Function
    if "NIST Function(s)" in crosswalk_df.columns:
        st.markdown('<p class="section-header">ISO Control Coverage per NIST Function</p>', unsafe_allow_html=True)
        fn_counts = crosswalk_df["NIST Function(s)"].value_counts().reset_index()
        fn_counts.columns = ["NIST Function", "ISO Controls Mapped"]
        fig_cov = px.bar(
            fn_counts,
            x="NIST Function", y="ISO Controls Mapped",
            color="ISO Controls Mapped",
            color_continuous_scale=["#2d3561","#64ffda"],
            template=PLOTLY_TEMPLATE,
            title="Number of ISO 27001 Controls Mapped per NIST CSF Function"
        )
        fig_cov.update_layout(coloraxis_showscale=False, xaxis_title="")
        st.plotly_chart(fig_cov, use_container_width=True)

    st.markdown('<p class="section-header">Crosswalk Detail</p>', unsafe_allow_html=True)

    cw_display_cols = [c for c in [
        "Control ID","Control Name","Domain","ISO Annex A Ref",
        "NIST CSF Subcategory(ies)","NIST Function(s)","Status","Notes"
    ] if c in filtered_cw.columns]

    cw_styled = filtered_cw[cw_display_cols].style.applymap(
        highlight_status, subset=["Status"] if "Status" in cw_display_cols else []
    )
    st.dataframe(cw_styled, use_container_width=True, height=500)
    st.caption(f"Showing {len(filtered_cw)} of {len(crosswalk_df)} crosswalk entries")


# ══════════════════════════════════════════════════════════
# TAB 5 ── RISK REGISTER
# Columns: Risk ID · Threat Scenario · Category · Threat Actor ·
#          Affected Assets · Vulnerability Exploited · Likelihood ·
#          Impact · Inherent Risk · Existing Controls ·
#          Control Effectiveness · Rating · Residual Risk ·
#          Risk Level · ISO 27001 Controls · NIST CSF Subcategories ·
#          GDPR Implication · Owner · Treatment & Action
# ══════════════════════════════════════════════════════════
with tab5:
    st.markdown('<p class="section-header">Risk Register — Threat Scenario Analysis</p>', unsafe_allow_html=True)

    # KPI row
    rk1, rk2, rk3, rk4 = st.columns(4)
    if "Risk Level" in risk_df.columns:
        rk1.metric("🔴 Critical", len(risk_df[risk_df["Risk Level"] == "Critical"]))
        rk2.metric("🟠 High",     len(risk_df[risk_df["Risk Level"] == "High"]))
        rk3.metric("🟡 Medium",   len(risk_df[risk_df["Risk Level"] == "Medium"]))
        rk4.metric("🟢 Low",      len(risk_df[risk_df["Risk Level"] == "Low"]))

    st.divider()

    col_r1, col_r2 = st.columns(2)

    # Heat map scatter
    with col_r1:
        st.markdown('<p class="section-header">Risk Heat Map</p>', unsafe_allow_html=True)
        req_risk = ["Likelihood","Impact","Inherent Risk","Risk Level"]
        if all(c in risk_df.columns for c in req_risk):
            fig_scatter = px.scatter(
                risk_df,
                x="Likelihood", y="Impact",
                size="Inherent Risk",
                color="Risk Level",
                hover_name="Threat Scenario",
                color_discrete_map=RISK_COLORS,
                template=PLOTLY_TEMPLATE,
                title="Likelihood vs Impact (bubble = Inherent Risk)",
                size_max=55
            )
            fig_scatter.update_layout(
                xaxis=dict(range=[0,6], dtick=1, title="Likelihood (1–5)"),
                yaxis=dict(range=[0,6], dtick=1, title="Impact (1–5)")
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

    # Inherent vs Residual comparison
    with col_r2:
        st.markdown('<p class="section-header">Inherent vs Residual Risk</p>', unsafe_allow_html=True)
        req_bar = ["Risk ID","Inherent Risk","Residual Risk"]
        if all(c in risk_df.columns for c in req_bar):
            fig_compare = go.Figure()
            fig_compare.add_trace(go.Bar(
                name="Inherent Risk",
                x=risk_df["Risk ID"],
                y=risk_df["Inherent Risk"],
                marker_color="#ff6b6b"
            ))
            fig_compare.add_trace(go.Bar(
                name="Residual Risk",
                x=risk_df["Risk ID"],
                y=risk_df["Residual Risk"],
                marker_color="#64ffda"
            ))
            fig_compare.update_layout(
                barmode="group",
                template=PLOTLY_TEMPLATE,
                title="Risk Reduction by Control Effectiveness",
                xaxis_title="Risk ID",
                yaxis_title="Risk Score"
            )
            st.plotly_chart(fig_compare, use_container_width=True)

    st.divider()

    # Full risk register table with filters
    st.markdown('<p class="section-header">Full Risk Register</p>', unsafe_allow_html=True)

    rf1, rf2, rf3 = st.columns(3)
    with rf1:
        level_opts = risk_df["Risk Level"].dropna().unique().tolist() if "Risk Level" in risk_df.columns else []
        level_filter = st.multiselect("Risk Level", options=level_opts, default=level_opts, key="risk_level")
    with rf2:
        cat_opts = risk_df["Category"].dropna().unique().tolist() if "Category" in risk_df.columns else []
        cat_filter = st.multiselect("Category", options=cat_opts, default=cat_opts, key="risk_cat")
    with rf3:
        owner_opts = risk_df["Owner"].dropna().unique().tolist() if "Owner" in risk_df.columns else []
        owner_filter = st.multiselect("Owner", options=owner_opts, default=owner_opts, key="risk_owner")

    filtered_risk = risk_df.copy()
    if level_filter  and "Risk Level" in filtered_risk.columns: filtered_risk = filtered_risk[filtered_risk["Risk Level"].isin(level_filter)]
    if cat_filter    and "Category"   in filtered_risk.columns: filtered_risk = filtered_risk[filtered_risk["Category"].isin(cat_filter)]
    if owner_filter  and "Owner"      in filtered_risk.columns: filtered_risk = filtered_risk[filtered_risk["Owner"].isin(owner_filter)]

    risk_display_cols = [c for c in [
        "Risk ID","Threat Scenario","Category","Threat Actor",
        "Likelihood","Impact","Inherent Risk","Control Effectiveness",
        "Rating","Residual Risk","Risk Level","Owner","Treatment & Action"
    ] if c in filtered_risk.columns]

    def highlight_risk_level(val):
        mapping = {
            "Critical": "background-color:#3d0d0d; color:#ff4444",
            "High":     "background-color:#3d1e0d; color:#ff8c00",
            "Medium":   "background-color:#3d3200; color:#ffd700",
            "Low":      "background-color:#0d3d2e; color:#64ffda"
        }
        return mapping.get(val, "")

    risk_styled = filtered_risk[risk_display_cols].style.applymap(
        highlight_risk_level,
        subset=["Risk Level"] if "Risk Level" in risk_display_cols else []
    )
    st.dataframe(risk_styled, use_container_width=True, height=420)
    st.caption(f"Showing {len(filtered_risk)} of {len(risk_df)} risk scenarios")


# ══════════════════════════════════════════════════════════
# TAB 6 ── STATEMENT OF APPLICABILITY
# Columns: Control ID · Annex A Control Name · Theme · ISO Ref ·
#          Applicable · Justification for Inclusion/Exclusion ·
#          Status · Control Owner · Evidence of Implementation ·
#          Gap/Notes · Linked Risk(s) · GDPR Article(s) · NIST CSF Mapping
# ══════════════════════════════════════════════════════════
with tab6:
    st.markdown('<p class="section-header">Statement of Applicability — ISO 27001 Clause 6.1.3</p>', unsafe_allow_html=True)

    # Summary metrics
    s1, s2, s3, s4 = st.columns(4)
    included  = len(soa_df[soa_df["Applicable"].str.upper() == "YES"]) if "Applicable" in soa_df.columns else 0
    excluded  = len(soa_df[soa_df["Applicable"].str.upper() == "NO"])  if "Applicable" in soa_df.columns else 0
    impl_soa  = len(soa_df[soa_df["Status"] == "Implemented"])         if "Status"     in soa_df.columns else 0
    part_soa  = len(soa_df[soa_df["Status"] == "Partially"])           if "Status"     in soa_df.columns else 0

    s1.metric("Controls Included",   included)
    s2.metric("Controls Excluded",   excluded)
    s3.metric("✅ Implemented",       impl_soa)
    s4.metric("🟡 Partially",         part_soa)

    st.divider()

    # Filters
    sf1, sf2, sf3 = st.columns(3)
    with sf1:
        theme_opts = soa_df["Theme"].dropna().unique().tolist() if "Theme" in soa_df.columns else []
        theme_filter = st.multiselect("Theme", options=theme_opts, default=theme_opts, key="soa_theme")
    with sf2:
        soa_status_opts = soa_df["Status"].dropna().unique().tolist() if "Status" in soa_df.columns else []
        soa_status_filter = st.multiselect("Status", options=soa_status_opts, default=soa_status_opts, key="soa_status")
    with sf3:
        soa_app_filter = st.multiselect("Applicable", options=["YES","NO","Yes","No"],
                                         default=["YES","Yes","NO","No"], key="soa_app")

    filtered_soa = soa_df.copy()
    if theme_filter      and "Theme"      in filtered_soa.columns: filtered_soa = filtered_soa[filtered_soa["Theme"].isin(theme_filter)]
    if soa_status_filter and "Status"     in filtered_soa.columns: filtered_soa = filtered_soa[filtered_soa["Status"].isin(soa_status_filter)]
    if soa_app_filter    and "Applicable" in filtered_soa.columns: filtered_soa = filtered_soa[filtered_soa["Applicable"].isin(soa_app_filter)]

    soa_display_cols = [c for c in [
        "Control ID","Annex A Control Name","Theme","ISO Ref","Applicable",
        "Justification for Inclusion/Exclusion","Status","Control Owner",
        "Evidence of Implementation","Gap/Notes","Linked Risk(s)",
        "GDPR Article(s)","NIST CSF Mapping"
    ] if c in filtered_soa.columns]

    soa_styled = filtered_soa[soa_display_cols].style.applymap(
        highlight_status,
        subset=["Status"] if "Status" in soa_display_cols else []
    )
    st.dataframe(soa_styled, use_container_width=True, height=520)
    st.caption(f"Showing {len(filtered_soa)} of {len(soa_df)} controls")


# ══════════════════════════════════════════════════════════
# TAB 7 ── REMEDIATION ROADMAP
# Columns: Action ID · Wave · Timeline · Control ID ·
#          Control Name · Remediation Action · Owner ·
#          Effort · Impact · Status
# ══════════════════════════════════════════════════════════
with tab7:
    st.markdown('<p class="section-header">Remediation Roadmap — Three-Wave Implementation Plan</p>', unsafe_allow_html=True)

    # Wave summary cards
    w1, w2, w3 = st.columns(3)
    wave_col = "Wave" if "Wave" in roadmap_df.columns else None

    if wave_col:
        w1_df = roadmap_df[roadmap_df[wave_col] == "Wave 1"]
        w2_df = roadmap_df[roadmap_df[wave_col] == "Wave 2"]
        w3_df = roadmap_df[roadmap_df[wave_col] == "Wave 3"]

        with w1:
            st.markdown("""
                <div style='background:#3d0d0d; border:1px solid #ff6b6b;
                            border-radius:10px; padding:16px; text-align:center;'>
                    <p style='color:#ff6b6b; font-family:"IBM Plex Mono",monospace;
                               font-size:0.7rem; letter-spacing:0.1em; margin:0;'>
                        WAVE 1 · 0–3 MONTHS
                    </p>
                    <p style='color:#ff6b6b; font-size:2rem; font-weight:700; margin:8px 0 4px 0;'>
                """ + str(len(w1_df)) + """
                    </p>
                    <p style='color:#8892b0; font-size:0.75rem; margin:0;'>Immediate Actions</p>
                </div>
            """, unsafe_allow_html=True)

        with w2:
            st.markdown("""
                <div style='background:#3d2e00; border:1px solid #ffd700;
                            border-radius:10px; padding:16px; text-align:center;'>
                    <p style='color:#ffd700; font-family:"IBM Plex Mono",monospace;
                               font-size:0.7rem; letter-spacing:0.1em; margin:0;'>
                        WAVE 2 · 3–6 MONTHS
                    </p>
                    <p style='color:#ffd700; font-size:2rem; font-weight:700; margin:8px 0 4px 0;'>
                """ + str(len(w2_df)) + """
                    </p>
                    <p style='color:#8892b0; font-size:0.75rem; margin:0;'>Short-Term Actions</p>
                </div>
            """, unsafe_allow_html=True)

        with w3:
            st.markdown("""
                <div style='background:#0d3d2e; border:1px solid #64ffda;
                            border-radius:10px; padding:16px; text-align:center;'>
                    <p style='color:#64ffda; font-family:"IBM Plex Mono",monospace;
                               font-size:0.7rem; letter-spacing:0.1em; margin:0;'>
                        WAVE 3 · 6–12 MONTHS
                    </p>
                    <p style='color:#64ffda; font-size:2rem; font-weight:700; margin:8px 0 4px 0;'>
                """ + str(len(w3_df)) + """
                    </p>
                    <p style='color:#8892b0; font-size:0.75rem; margin:0;'>Medium-Term Actions</p>
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Gantt timeline
    st.markdown('<p class="section-header">Implementation Timeline</p>', unsafe_allow_html=True)

    action_col = next(
        (c for c in ["Remediation Action","Action","Control Name"] if c in roadmap_df.columns),
        roadmap_df.columns[2] if len(roadmap_df.columns) > 2 else None
    )

    wave_config = {
        "Wave 1": {"start": 0,  "end": 3,  "color": "#ff6b6b"},
        "Wave 2": {"start": 3,  "end": 6,  "color": "#ffd700"},
        "Wave 3": {"start": 6,  "end": 12, "color": "#64ffda"}
    }

    if wave_col and action_col:
        fig_gantt = go.Figure()
        for wave_name, config in wave_config.items():
            wave_data = roadmap_df[roadmap_df[wave_col] == wave_name]
            for _, row in wave_data.iterrows():
                fig_gantt.add_trace(go.Bar(
                    x=[config["end"] - config["start"]],
                    y=[str(row.get(action_col, ""))[:60]],  # truncate long names
                    base=config["start"],
                    orientation="h",
                    marker_color=config["color"],
                    name=wave_name,
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{wave_name}</b><br>"
                        f"Month {config['start']}–{config['end']}<br>"
                        f"Owner: {row.get('Owner','N/A')}"
                        "<extra></extra>"
                    )
                ))
        fig_gantt.update_layout(
            barmode="overlay",
            template=PLOTLY_TEMPLATE,
            xaxis=dict(title="Month", dtick=1, range=[0,13]),
            yaxis=dict(title="", autorange="reversed"),
            height=max(400, len(roadmap_df) * 28),
            title="Remediation Actions — Gantt Timeline"
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

    st.divider()

    # Filters and table
    st.markdown('<p class="section-header">Roadmap Detail</p>', unsafe_allow_html=True)

    rm1, rm2, rm3 = st.columns(3)
    with rm1:
        wave_filter = st.multiselect(
            "Wave", options=["Wave 1","Wave 2","Wave 3"],
            default=["Wave 1","Wave 2","Wave 3"], key="rm_wave"
        )
    with rm2:
        effort_opts = roadmap_df["Effort"].dropna().unique().tolist() if "Effort" in roadmap_df.columns else []
        effort_filter = st.multiselect("Effort", options=effort_opts, default=effort_opts, key="rm_effort")
    with rm3:
        rm_status_opts = roadmap_df["Status"].dropna().unique().tolist() if "Status" in roadmap_df.columns else []
        rm_status_filter = st.multiselect("Status", options=rm_status_opts, default=rm_status_opts, key="rm_status")

    filtered_rm = roadmap_df.copy()
    if wave_filter      and wave_col                          : filtered_rm = filtered_rm[filtered_rm[wave_col].isin(wave_filter)]
    if effort_filter    and "Effort" in filtered_rm.columns   : filtered_rm = filtered_rm[filtered_rm["Effort"].isin(effort_filter)]
    if rm_status_filter and "Status" in filtered_rm.columns   : filtered_rm = filtered_rm[filtered_rm["Status"].isin(rm_status_filter)]

    rm_display_cols = [c for c in [
        "Action ID","Wave","Timeline","Control ID","Control Name",
        "Remediation Action","Owner","Effort","Impact","Status"
    ] if c in filtered_rm.columns]

    st.dataframe(filtered_rm[rm_display_cols], use_container_width=True, height=420)
    st.caption(f"Showing {len(filtered_rm)} of {len(roadmap_df)} remediation actions")

# ══════════════════════════════════════════════════════════
# TAB 8 ── GDPR REGULATORY MAPPING
# Columns: Control ID · Control Name · Domain · ISO 27001 Ref ·
#          NIST CSF Mapping · GDPR Article(s) · Article Title ·
#          GDPR Obligation Description · Helion's Compliance Evidence ·
#          GAP vs GDPR Requirement · Linked Risk · Status ·
#          Recommended Action
# ══════════════════════════════════════════════════════════
with tab8:
    st.markdown('<p class="section-header">GDPR Regulatory Mapping</p>', unsafe_allow_html=True)

    st.info(
        "Maps ISO 27001 controls to specific GDPR articles, identifying active violations, "
        "compliance gaps, and recommended remediation actions. "
        "Active violations are highlighted in red — these represent current non-compliance, "
        "not just risk of future non-compliance.",
        icon="🇪🇺"
    )

    # ── KPI row ──
    g1, g2, g3, g4 = st.columns(4)

    if "Status" in gdpr_df.columns:
        gdpr_compliant    = len(gdpr_df[gdpr_df["Status"].str.lower().isin(["compliant","implemented"])])
        gdpr_partial      = len(gdpr_df[gdpr_df["Status"].str.lower().isin(["partially","partial"])])
        gdpr_non          = len(gdpr_df[gdpr_df["Status"].str.lower().isin(["non-compliant","not implemented","violation"])])
        gdpr_total        = len(gdpr_df)

        g1.metric("Total Controls Mapped", gdpr_total)
        g2.metric("✅ Compliant",           gdpr_compliant)
        g3.metric("🟡 Partially Compliant", gdpr_partial)
        g4.metric("🔴 Non-Compliant",       gdpr_non)

    st.divider()

    # ── GDPR Article coverage chart ──
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown('<p class="section-header">Controls per GDPR Article</p>', unsafe_allow_html=True)
        if "GDPR Article(s)" in gdpr_df.columns:
            article_counts = gdpr_df["GDPR Article(s)"].value_counts().reset_index()
            article_counts.columns = ["GDPR Article", "Count"]
            fig_articles = px.bar(
                article_counts,
                x="Count", y="GDPR Article",
                orientation="h",
                color="Count",
                color_continuous_scale=["#2d3561", "#64ffda"],
                template=PLOTLY_TEMPLATE,
                title="ISO Controls Mapped per GDPR Article"
            )
            fig_articles.update_layout(
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                margin=dict(t=40, b=20)
            )
            st.plotly_chart(fig_articles, use_container_width=True)

    with col_g2:
        st.markdown('<p class="section-header">Compliance Status Distribution</p>', unsafe_allow_html=True)
        if "Status" in gdpr_df.columns:
            gdpr_status_counts = gdpr_df["Status"].value_counts().reset_index()
            gdpr_status_counts.columns = ["Status", "Count"]

            gdpr_color_map = {
                "Compliant":       "#64ffda",
                "Implemented":     "#64ffda",
                "Partially":       "#ffd700",
                "Partial":         "#ffd700",
                "Non-Compliant":   "#ff6b6b",
                "Not Implemented": "#ff6b6b",
                "Violation":       "#ff4444"
            }

            fig_gdpr_donut = px.pie(
                gdpr_status_counts,
                values="Count", names="Status",
                hole=0.55,
                color="Status",
                color_discrete_map=gdpr_color_map,
                template=PLOTLY_TEMPLATE
            )
            fig_gdpr_donut.update_traces(textposition="inside", textinfo="percent+label")
            fig_gdpr_donut.update_layout(showlegend=False, margin=dict(t=20,b=20,l=20,r=20))
            st.plotly_chart(fig_gdpr_donut, use_container_width=True)

    st.divider()

    # ── Filters ──
    st.markdown('<p class="section-header">GDPR Mapping Detail</p>', unsafe_allow_html=True)

    gf1, gf2, gf3 = st.columns(3)

    with gf1:
        gdpr_status_opts = gdpr_df["Status"].dropna().unique().tolist() if "Status" in gdpr_df.columns else []
        gdpr_status_filter = st.multiselect(
            "Compliance Status", options=gdpr_status_opts,
            default=gdpr_status_opts, key="gdpr_status"
        )

    with gf2:
        gdpr_domain_opts = gdpr_df["Domain"].dropna().unique().tolist() if "Domain" in gdpr_df.columns else []
        gdpr_domain_filter = st.multiselect(
            "Domain", options=gdpr_domain_opts,
            default=gdpr_domain_opts, key="gdpr_domain"
        )

    with gf3:
        gdpr_article_opts = gdpr_df["GDPR Article(s)"].dropna().unique().tolist() if "GDPR Article(s)" in gdpr_df.columns else []
        gdpr_article_filter = st.multiselect(
            "GDPR Article", options=gdpr_article_opts,
            default=gdpr_article_opts, key="gdpr_article"
        )

    # Apply filters
    filtered_gdpr = gdpr_df.copy()
    if gdpr_status_filter  and "Status"        in filtered_gdpr.columns: filtered_gdpr = filtered_gdpr[filtered_gdpr["Status"].isin(gdpr_status_filter)]
    if gdpr_domain_filter  and "Domain"        in filtered_gdpr.columns: filtered_gdpr = filtered_gdpr[filtered_gdpr["Domain"].isin(gdpr_domain_filter)]
    if gdpr_article_filter and "GDPR Article(s)" in filtered_gdpr.columns: filtered_gdpr = filtered_gdpr[filtered_gdpr["GDPR Article(s)"].isin(gdpr_article_filter)]

    # Colour status column
    def highlight_gdpr_status(val):
        val_lower = str(val).lower()
        if val_lower in ["compliant", "implemented"]:
            return "background-color:#0d3d2e; color:#64ffda"
        elif val_lower in ["partially", "partial"]:
            return "background-color:#3d2e0d; color:#ffd700"
        elif val_lower in ["non-compliant", "not implemented", "violation"]:
            return "background-color:#3d0d0d; color:#ff6b6b"
        return ""

    gdpr_display_cols = [c for c in [
        "Control ID", "Control Name", "Domain", "ISO 27001 Ref",
        "NIST CSF Mapping", "GDPR Article(s)", "Article Title",
        "GDPR Obligation Description", "Helion's Compliance Evidence",
        "GAP vs GDPR Requirement", "Linked Risk", "Status",
        "Recommended Action"
    ] if c in filtered_gdpr.columns]

    gdpr_styled = filtered_gdpr[gdpr_display_cols].style.applymap(
        highlight_gdpr_status,
        subset=["Status"] if "Status" in gdpr_display_cols else []
    )

    st.dataframe(gdpr_styled, use_container_width=True, height=520)
    st.caption(f"Showing {len(filtered_gdpr)} of {len(gdpr_df)} GDPR mappings")

    # ── Active violations callout ──
    if "Status" in gdpr_df.columns:
        violations = gdpr_df[gdpr_df["Status"].str.lower().isin(
            ["non-compliant", "not implemented", "violation"]
        )]
        if len(violations) > 0:
            st.divider()
            st.markdown('<p class="section-header">⚠️ Active Compliance Violations</p>', unsafe_allow_html=True)
            st.error(
                f"**{len(violations)} active GDPR compliance violation(s) identified** — "
                "these represent current non-compliance requiring immediate remediation.",
                icon="🚨"
            )
            violation_cols = [c for c in [
                "Control ID", "Control Name", "GDPR Article(s)",
                "Article Title", "GAP vs GDPR Requirement", "Recommended Action"
            ] if c in violations.columns]
            st.dataframe(violations[violation_cols], use_container_width=True)

# ══════════════════════════════════════════════════════════
# TAB 9 ── TPRM PROGRAM
# ══════════════════════════════════════════════════════════
with tab9:
    st.markdown('<p class="section-header">Third-Party Risk Management (TPRM) Program</p>', unsafe_allow_html=True)

    # ── KPI row from inventory ──
    t1, t2, t3, t4, t5 = st.columns(5)
    total_vendors = len(tprm_inv_df) if not tprm_inv_df.empty else 0
    critical_v = len(tprm_inv_df[tprm_inv_df["Initial Risk Tier"] == "Critical"]) if "Initial Risk Tier" in tprm_inv_df.columns else 0
    high_v = len(tprm_inv_df[tprm_inv_df["Initial Risk Tier"] == "High"]) if "Initial Risk Tier" in tprm_inv_df.columns else 0
    dpa_violations = len(tprm_inv_df[tprm_inv_df["DPA in Place"] == "No"]) if "DPA in Place" in tprm_inv_df.columns else 0
    assessed = len(tprm_inv_df[tprm_inv_df["Assessment Status"] == "Completed"]) if "Assessment Status" in tprm_inv_df.columns else 0

    t1.metric("Total Vendors", total_vendors)
    t2.metric("🔴 Critical Tier", critical_v)
    t3.metric("🟠 High Tier", high_v)
    t4.metric("⚠️ DPA Violations", dpa_violations)
    t5.metric("✅ Assessments Complete", assessed)

    st.divider()

    col_tl, col_tr = st.columns(2)

    with col_tl:
        st.markdown('<p class="section-header">Vendor Distribution by Risk Tier</p>', unsafe_allow_html=True)
        if "Initial Risk Tier" in tprm_inv_df.columns:
            tier_counts = tprm_inv_df["Initial Risk Tier"].value_counts().reset_index()
            tier_counts.columns = ["Tier", "Count"]
            tier_color_map = {
                "Critical": "#ff6b6b",
                "High":     "#ffd700",
                "Medium":   "#64ffda",
                "Low":      "#4a9eff",
            }
            fig_tier = px.bar(
                tier_counts,
                x="Tier", y="Count",
                color="Tier",
                color_discrete_map=tier_color_map,
                template=PLOTLY_TEMPLATE,
                title="Vendors by Risk Tier"
            )
            fig_tier.update_layout(showlegend=False, xaxis_title="", yaxis_title="Vendors")
            st.plotly_chart(fig_tier, use_container_width=True)

    with col_tr:
        st.markdown('<p class="section-header">Assessment Status Overview</p>', unsafe_allow_html=True)
        if "Assessment Status" in tprm_inv_df.columns:
            status_counts = tprm_inv_df["Assessment Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            status_color_map = {
                "Completed":    "#64ffda",
                "In Progress":  "#ffd700",
                "Pending":      "#ff8c00",
                "Not Required": "#4a5568",
                "Overdue":      "#ff4444",
            }
            fig_status = px.pie(
                status_counts,
                values="Count", names="Status",
                hole=0.55,
                color="Status",
                color_discrete_map=status_color_map,
                template=PLOTLY_TEMPLATE
            )
            fig_status.update_traces(textposition="inside", textinfo="percent+label")
            fig_status.update_layout(showlegend=False, margin=dict(t=20,b=20,l=20,r=20))
            st.plotly_chart(fig_status, use_container_width=True)

    st.divider()

    # ── Vendor Inventory table ──
    st.markdown('<p class="section-header">Vendor Inventory</p>', unsafe_allow_html=True)

    ti1, ti2 = st.columns(2)
    with ti1:
        tier_filter_opts = tprm_inv_df["Initial Risk Tier"].dropna().unique().tolist() if "Initial Risk Tier" in tprm_inv_df.columns else []
        tier_filter_tprm = st.multiselect("Filter by Tier", options=tier_filter_opts, default=tier_filter_opts, key="tprm_tier")
    with ti2:
        astatus_opts = tprm_inv_df["Assessment Status"].dropna().unique().tolist() if "Assessment Status" in tprm_inv_df.columns else []
        astatus_filter = st.multiselect("Filter by Assessment Status", options=astatus_opts, default=astatus_opts, key="tprm_astatus")

    filtered_inv = tprm_inv_df.copy()
    if tier_filter_tprm and "Initial Risk Tier" in filtered_inv.columns:
        filtered_inv = filtered_inv[filtered_inv["Initial Risk Tier"].isin(tier_filter_tprm)]
    if astatus_filter and "Assessment Status" in filtered_inv.columns:
        filtered_inv = filtered_inv[filtered_inv["Assessment Status"].isin(astatus_filter)]

    def highlight_tier(val):
        colors = {
            "Critical": "background-color:#3C3489; color:#EEEDFE",
            "High":     "background-color:#BA7517; color:#FAEEDA",
            "Medium":   "background-color:#3B6D11; color:#EAF3DE",
            "Low":      "background-color:#185FA5; color:#E6F1FB",
        }
        return colors.get(val, "")

    def highlight_dpa(val):
        if val == "Yes": return "background-color:#0d3d2e; color:#64ffda"
        if val in ["No", "No — VIOLATION"]: return "background-color:#3d0d0d; color:#ff6b6b"
        return ""

    inv_cols = [c for c in [
        "Vendor ID","Vendor Name","Service Category","Initial Risk Tier",
        "Personal Data Processed","Service Criticality","Assessment Status",
        "Last Assessment Date","Next Assessment Due","DPA in Place","Notes"
    ] if c in filtered_inv.columns]

    if inv_cols:
        styled_inv = filtered_inv[inv_cols].style
        if "Initial Risk Tier" in inv_cols:
            styled_inv = styled_inv.applymap(highlight_tier, subset=["Initial Risk Tier"])
        if "DPA in Place" in inv_cols:
            styled_inv = styled_inv.applymap(highlight_dpa, subset=["DPA in Place"])
        st.dataframe(styled_inv, use_container_width=True, height=400)
    st.caption(f"Showing {len(filtered_inv)} of {len(tprm_inv_df)} vendors")

    st.divider()

    # ── Vendor Risk Register ──
    st.markdown('<p class="section-header">Vendor Risk Register — Assessed Vendors</p>', unsafe_allow_html=True)

    if not tprm_reg_df.empty:
        reg_cols = [c for c in [
            "Vendor ID","Vendor Name","Service Category","Risk Tier",
            "Assessment Date","Score %","Risk Rating","Key Findings",
            "Required Remediations","Remediation Deadline","Remediation Status",
            "Next Assessment Due","DPA in Place","Assessment Status"
        ] if c in tprm_reg_df.columns]

        if reg_cols:
            st.dataframe(tprm_reg_df[reg_cols], use_container_width=True, height=380)

    st.divider()

    # ── Remediation Tracker ──
    st.markdown('<p class="section-header">Remediation Tracker</p>', unsafe_allow_html=True)

    if not tprm_rem_df.empty:
        rem1, rem2 = st.columns(2)
        with rem1:
            rem_vendor_opts = tprm_rem_df["Vendor Name"].dropna().unique().tolist() if "Vendor Name" in tprm_rem_df.columns else []
            rem_vendor_filter = st.multiselect("Filter by Vendor", options=rem_vendor_opts, default=rem_vendor_opts, key="rem_vendor")
        with rem2:
            rem_status_opts = tprm_rem_df["Status"].dropna().unique().tolist() if "Status" in tprm_rem_df.columns else []
            rem_status_filter = st.multiselect("Filter by Status", options=rem_status_opts, default=rem_status_opts, key="rem_status")

        filtered_rem = tprm_rem_df.copy()
        if rem_vendor_filter and "Vendor Name" in filtered_rem.columns:
            filtered_rem = filtered_rem[filtered_rem["Vendor Name"].isin(rem_vendor_filter)]
        if rem_status_filter and "Status" in filtered_rem.columns:
            filtered_rem = filtered_rem[filtered_rem["Status"].isin(rem_status_filter)]

        rem_cols = [c for c in [
            "Vendor ID","Vendor Name","Risk Tier","Priority",
            "Remediation Required","Owner","Deadline","Status",
            "Evidence of Completion","Notes"
        ] if c in filtered_rem.columns]

        if rem_cols:
            def highlight_priority(val):
                if "P1" in str(val): return "background-color:#3d0d0d; color:#ff6b6b"
                if "P2" in str(val): return "background-color:#3d2e0d; color:#ffd700"
                if "P3" in str(val): return "background-color:#0d1f3d; color:#4a9eff"
                return ""

            def highlight_rem_status(val):
                colors = {
                    "Completed":    "background-color:#0d3d2e; color:#64ffda",
                    "In Progress":  "background-color:#3d2e0d; color:#ffd700",
                    "Not Started":  "background-color:#3d0d0d; color:#ff6b6b",
                    "Pending":      "background-color:#3d2e0d; color:#ffd700",
                }
                return colors.get(val, "")

            rem_styled = filtered_rem[rem_cols].style
            if "Priority" in rem_cols:
                rem_styled = rem_styled.applymap(highlight_priority, subset=["Priority"])
            if "Status" in rem_cols:
                rem_styled = rem_styled.applymap(highlight_rem_status, subset=["Status"])
            st.dataframe(rem_styled, use_container_width=True, height=420)
            st.caption(f"Showing {len(filtered_rem)} of {len(tprm_rem_df)} remediation actions")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.divider()
st.markdown("""
    <p style='text-align:center; color:#4a5568; font-size:0.75rem;
              font-family:"IBM Plex Mono",monospace;'>
        Helion GRC Dashboard · ISO/IEC 27001:2022 + NIST CSF 2.0 + GDPR ·
        Built by Aryan Bhosale · ISO 27001 Lead Implementer (TÜV SÜD) ·
        GWU MS Cybersecurity
    </p>
""", unsafe_allow_html=True)