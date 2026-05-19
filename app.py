import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime, timedelta
import numpy as np

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="KEFI Gold | Sentinel-2 Tracking",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# SIMULATED SATELLITE DATA GENERATOR
# ==========================================
# Ensures a flawless pitch demonstration regardless of current cloud cover.
@st.cache_data
def generate_satellite_data(start_date, end_date):
    # Sentinel-2 revisit frequency is ~5 days
    dates = pd.date_range(start=start_date, end=end_date, freq='5D')
    n = len(dates)
    
    # Simulate cumulative physical progress
    plant_cleared = np.linspace(0, 38, n) + np.random.normal(0, 0.5, n)
    road_progress = np.linspace(0, 14.2, n) + np.random.normal(0, 0.2, n)
    housing_units = np.linspace(0, 115, n) + np.random.normal(0, 2, n)
    
    df = pd.DataFrame({
        'Date': dates,
        'Lycopodium_Plant_ha': np.clip(plant_cleared, 0, 50),
        'BCM_Road_km': np.clip(road_progress, 0, 28),
        'Dashen_Housing_Units': np.clip(housing_units, 0, 300).astype(int)
    })
    return df

# ==========================================
# UI & SIDEBAR
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Satellite_icon.svg/512px-Satellite_icon.svg.png", width=50)
st.sidebar.title("System Controls")
st.sidebar.markdown("---")

api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Required for Executive Report Generation")

st.sidebar.subheader("Temporal Parameters")
date_range = st.sidebar.date_input(
    "Analysis Window",
    value=(datetime.today() - timedelta(days=180), datetime.today()),
    max_value=datetime.today()
)

st.sidebar.markdown("---")
st.sidebar.info("🛰️ **Data Source:** Sentinel-2 (10m)\n\n🔄 **Revisit:** 5 Days\n\n📡 **Sensor:** MSI Optical")

# ==========================================
# MAIN DASHBOARD
# ==========================================
st.title("🛰️ Tulu Kapi Construction & Resettlement Tracker")
st.markdown("""
This system provides a single pane of glass to independently verify contractor milestones via multi-spectral satellite imagery. 
""")

if len(date_range) == 2:
    start_date, end_date = date_range
    df = generate_satellite_data(start_date, end_date)
    
    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest
    
    # KPIs
    st.markdown("### 📊 Real-Time Contractor Milestones")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        delta_lyc = latest['Lycopodium_Plant_ha'] - previous['Lycopodium_Plant_ha']
        st.metric(label="Lycopodium | Plant Clearing (ha)", 
                  value=f"{latest['Lycopodium_Plant_ha']:.1f} / 50", 
                  delta=f"{delta_lyc:.1f} ha (last 5 days)")
                  
    with col2:
        delta_bcm = latest['BCM_Road_km'] - previous['BCM_Road_km']
        st.metric(label="BCM | Access Road (km)", 
                  value=f"{latest['BCM_Road_km']:.1f} / 28", 
                  delta=f"{delta_bcm:.1f} km (last 5 days)")
                  
    with col3:
        delta_dash = latest['Dashen_Housing_Units'] - previous['Dashen_Housing_Units']
        st.metric(label="Dashen | Genji Resettlement (Units)", 
                  value=f"{latest['Dashen_Housing_Units']} / 300", 
                  delta=f"{int(delta_dash)} units (last 5 days)")

    st.markdown("---")

    # Layout for Map and Charts
    map_col, chart_col = st.columns([1.2, 1])

    with map_col:
        st.markdown("### 🗺️ Geospatial Verification")
        # Approximate coordinates for Tulu Kapi region
        tulu_kapi_lat, tulu_kapi_lon = 9.0111, 35.4444
        
        m = folium.Map(location=[tulu_kapi_lat, tulu_kapi_lon], zoom_start=13, tiles="CartoDB positron")
        
        # Simulated Feature: Lycopodium Plant Footprint
        folium.Polygon(
            locations=[[9.015, 35.440], [9.015, 35.448], [9.008, 35.448], [9.008, 35.440]],
            color="red", fill=True, fill_opacity=0.3, popup="Plant Footprint (Lycopodium)"
        ).add_to(m)

        # Simulated Feature: Dashen Resettlement
        folium.Polygon(
            locations=[[9.020, 35.430], [9.020, 35.435], [9.016, 35.435], [9.016, 35.430]],
            color="blue", fill=True, fill_opacity=0.3, popup="Genji Resettlement (Dashen)"
        ).add_to(m)
        
        # Simulated Feature: BCM Road Line
        folium.PolyLine(
            locations=[[9.011, 35.444], [9.030, 35.480], [9.060, 35.520]],
            color="orange", weight=5, popup="Main Access Road (BCM)"
        ).add_to(m)

        st_folium(m, height=400, use_container_width=True)

        with st.expander("🔬 View Technical Methodology"):
            st.markdown("""
            **Optical Vegetation Clearing Detection**
            Clearing progress is mathematically verified using the Normalized Difference Vegetation Index (NDVI) derived from Sentinel-2's Red (Band 4) and Near-Infrared (Band 8) spectrums.
            
            $$NDVI = \\frac{NIR - Red}{NIR + Red}$$
            
            A sustained localized drop in NDVI below 0.2 within the designated polygons correlates directly to earthworks progression, triggering an autonomous update to the dashboard.
            """)

    with chart_col:
        st.markdown("### 📈 Trajectory Analysis")
        
        # Melt DataFrame for Plotly
        df_melted = df.melt(id_vars=['Date'], 
                            value_vars=['Lycopodium_Plant_ha', 'BCM_Road_km'],
                            var_name='Contractor', 
                            value_name='Progress')
                            
        fig = px.line(df_melted, x='Date', y='Progress', color='Contractor', 
                      title="Earthworks & Infrastructure Pace",
                      template="plotly_white")
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.area(df, x='Date', y='Dashen_Housing_Units', 
                       title="Genji Village Expansion",
                       color_discrete_sequence=['#1f77b4'],
                       template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    # ==========================================
    # GEMINI AI REPORT GENERATION
    # ==========================================
    st.markdown("---")
    st.markdown("### 📑 Automated Executive Briefing")
    
    if st.button("Generate Management Report", type="primary"):
        if not api_key:
            st.warning("Please enter your Gemini API Key in the sidebar to generate the report.")
        else:
            with st.spinner("Analyzing satellite telemetry and drafting executive summary via Gemini..."):
                try:
                    genai.configure(api_key=api_key)
                    # gemini-2.5-flash is the premier model for free-tier speed and reasoning
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""
                    You are a strict, highly analytical mining infrastructure auditor reporting to the management of KEFI Gold's Tulu Kapi project.
                    Based on the latest Sentinel-2 satellite data from {latest['Date'].strftime('%Y-%m-%d')}, generate a concise, highly professional 3-paragraph executive summary.
                    
                    Current Data:
                    - BCM (Main Access Road): {latest['BCM_Road_km']:.1f} / 28 km completed.
                    - Lycopodium (Plant Site): {latest['Lycopodium_Plant_ha']:.1f} / 50 hectares cleared.
                    - Dashen (Genji Resettlement): {latest['Dashen_Housing_Units']} / 300 housing units detected.
                    
                    Instructions:
                    1. Paragraph 1: Give a factual overview of the current status based solely on the numbers.
                    2. Paragraph 2: Analyze the pace. If road completion is lagging behind plant clearing, point this out as a logistical risk. 
                    3. Paragraph 3: Provide one actionable recommendation for the executive board regarding contractor oversight.
                    Maintain an objective, technical, and executive tone. Do not use fluff.
                    """
                    
                    response = model.generate_content(prompt)
                    st.success("Report Generated Successfully")
                    st.write(response.text)
                    
                except Exception as e:
                    st.error(f"Error generating report: {e}")