import streamlit as st
import json
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import base64
import google.generativeai as genai

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Tulu Kapi Tracker", page_icon="🛰️", layout="wide")

st.markdown("""
    <style>
    .metric-container { display: flex; flex-direction: column; }
    .metric-title { font-size: 12px; color: #a0aec0; margin-bottom: -10px;}
    .metric-value { font-size: 32px; font-weight: bold; color: white; }
    .metric-target { font-size: 18px; color: #a0aec0; }
    .metric-delta { font-size: 14px; color: #48bb78; }
    .metric-delta.negative { color: #f56565; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# PROJECT TARGETS
# ==========================================
TARGETS = {
    "plant": 100,
    "road": 200,
    "genji": 500
}

# ==========================================
# LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    try:
        with open("data/metrics.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("🚨 Data not found. Run `python extractor.py` first.")
        st.stop()

def get_image_base64(filepath):
    try:
        with open(filepath, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return None

data = load_data()
df_plant = pd.DataFrame(data['plant']['history'])
df_road = pd.DataFrame(data['road']['history'])
df_genji = pd.DataFrame(data['genji']['history'])

# ==========================================
# DATA SMOOTHING (CUMULATIVE MAX FILTER)
# ==========================================
def apply_cummax_filter(df):
    if not df.empty and 'value' in df.columns:
        df['value'] = df['value'].replace(0.0, pd.NA)
        df['value'] = df['value'].ffill()
        df['value'] = df['value'].cummax()
        df['value'] = df['value'].fillna(0)
    return df

df_plant = apply_cummax_filter(df_plant)
df_road = apply_cummax_filter(df_road)
df_genji = apply_cummax_filter(df_genji)

# ==========================================
# SIDEBAR & DATE FILTER
# ==========================================
st.sidebar.title("System Controls")

st.sidebar.markdown("### 📅 Temporal Parameters")
if not df_plant.empty:
    df_plant['date'] = pd.to_datetime(df_plant['date'])
    df_road['date'] = pd.to_datetime(df_road['date'])
    df_genji['date'] = pd.to_datetime(df_genji['date'])
    
    min_date = df_plant['date'].min().date()
    max_date = df_plant['date'].max().date()
    
    date_range = st.sidebar.slider("Analysis Window", min_value=min_date, max_value=max_date, value=(min_date, max_date))
    
    mask_plant = (df_plant['date'].dt.date >= date_range[0]) & (df_plant['date'].dt.date <= date_range[1])
    df_plant_filtered = df_plant.loc[mask_plant].reset_index(drop=True)
    
    mask_road = (df_road['date'].dt.date >= date_range[0]) & (df_road['date'].dt.date <= date_range[1])
    df_road_filtered = df_road.loc[mask_road].reset_index(drop=True)
    
    mask_genji = (df_genji['date'].dt.date >= date_range[0]) & (df_genji['date'].dt.date <= date_range[1])
    df_genji_filtered = df_genji.loc[mask_genji].reset_index(drop=True)
else:
    st.sidebar.warning("No historical data available. Run extraction again.")
    df_plant_filtered, df_road_filtered, df_genji_filtered = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.info("🛰️ **Data Source:** Sentinel-2 (10m)\n\n🔄 **Revisit:** 5 Days\n\n📷 **Sensor:** MSI Optical")

# ==========================================
# DYNAMIC METRIC CALCULATION
# ==========================================
def calc_dynamic_metrics(df):
    if df.empty or len(df) < 1:
        return 0.0, 0.0
    current = df.iloc[-1]['value']
    delta = current - df.iloc[0]['value'] if len(df) > 1 else 0.0
    return current, round(delta, 1)

p_curr, p_delta = calc_dynamic_metrics(df_plant_filtered)
r_curr, r_delta = calc_dynamic_metrics(df_road_filtered)
g_curr, g_delta = calc_dynamic_metrics(df_genji_filtered)

# ==========================================
# MAIN DASHBOARD
# ==========================================
st.title("🛰️ Tulu Kapi Construction & Resettlement Tracker")

st.markdown("### 📊 Real-Time Contractor Milestones")
col1, col2, col3 = st.columns(3)

def render_metric(col, title, current, target, delta, unit):
    arrow = "↑" if delta >= 0 else "↓"
    color_class = "" if delta >= 0 else "negative"
    with col:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">{title}</div>
            <div><span class="metric-value">{current}</span><span class="metric-target"> / {target}</span></div>
            <div class="metric-delta {color_class}">{arrow} {abs(delta)} {unit} (in selected window)</div>
        </div>
        """, unsafe_allow_html=True)

render_metric(col1, "Lycopodium | Plant Clearing (ha)", p_curr, TARGETS["plant"], p_delta, "ha")
render_metric(col2, "BCM | Access Road (km)", r_curr, TARGETS["road"], r_delta, "km")
render_metric(col3, "Dashen | Genji Resettlement (Units)", int(g_curr), TARGETS["genji"], int(g_delta), "units")

st.markdown("---")

# ==========================================
# MAP & CHARTS
# ==========================================
col_map, col_charts = st.columns([1, 1.2])

with col_map:
    st.markdown("### 🗺️ Geospatial Verification")
    m = folium.Map(location=[9.0819, 35.5517], zoom_start=14, tiles="CartoDB positron")
    
    img_base64 = get_image_base64("data/latest_view.jpg")
    if img_base64:
        img_html = f"data:image/jpeg;base64,{img_base64}"
        bounds = [[9.065, 35.535], [9.095, 35.565]]
        folium.raster_layers.ImageOverlay(
            image=img_html,
            bounds=bounds,
            opacity=1.0,
            name="Copernicus Sentinel-2 RGB"
        ).add_to(m)

    folium.Polygon(locations=[[9.078, 35.548], [9.078, 35.553], [9.083, 35.553], [9.083, 35.548]], color="blue", fill=False).add_to(m)
    folium.Polygon(locations=[[9.070, 35.540], [9.070, 35.550], [9.080, 35.550], [9.080, 35.540]], color="orange", fill=False).add_to(m)
    folium.Polygon(locations=[[9.085, 35.555], [9.085, 35.560], [9.090, 35.560], [9.090, 35.555]], color="green", fill=False).add_to(m)
    
    st_folium(m, height=450, use_container_width=True)
    
    # 1. Technical Methodology Expander
    with st.expander("🔬 View Technical Methodology"):
        st.markdown("""
        **Optical Vegetation Clearing Detection**  
        Clearing progress is mathematically verified utilizing the European Space Agency's Sentinel-2 satellite (10m spatial resolution). The algorithm calculates the Normalized Difference Vegetation Index (NDVI) derived from the sensor's Red (Band 4) and Near-Infrared (Band 8) spectrums.
        """)
        
        st.latex(r"NDVI = \frac{NIR - Red}{NIR + Red}")
        
        st.markdown("""
        A sustained localized drop in NDVI below 0.30 within the designated polygons is geometrically mapped and cross-verified against cloud data-masks. This correlates directly to earthworks progression, triggering an autonomous, tamper-proof update to the dashboard.
        """)

with col_charts:
    st.markdown("### 📈 Trajectory Analysis")
    
    if not df_plant_filtered.empty and not df_road_filtered.empty:
        df_p_chart = df_plant_filtered.copy()
        df_r_chart = df_road_filtered.copy()
        df_p_chart['Contractor'] = 'Lycopodium_Plant_ha'
        df_r_chart['Contractor'] = 'BCM_Road_ha'
        df_combined = pd.concat([df_p_chart, df_r_chart])
        
        fig1 = px.line(df_combined, x="date", y="value", color='Contractor', 
                       color_discrete_map={'Lycopodium_Plant_ha': 'blue', 'BCM_Road_ha': 'orange'},
                       template="plotly_dark", title="Earthworks & Infrastructure Pace")
        fig1.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250, yaxis_title="Hectares")
        st.plotly_chart(fig1, use_container_width=True)

    if not df_genji_filtered.empty:
        fig2 = px.area(df_genji_filtered, x="date", y="value", template="plotly_dark", title="Genji Village Expansion")
        fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250, yaxis_title="Housing Units")
        st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# 2. AUTOMATED EXECUTIVE BRIEFING
# ==========================================
st.markdown("---")
st.markdown("### 📑 Automated Executive Briefing")

# Define the Prompt
prompt = f"""
You are an independent consultant generating a formal executive briefing for the management of KEFI Gold and Copper regarding the Tulu Kapi Gold Project. 
Review the latest verified satellite telemetry metrics:

1. Plant Site Clearing (Contractor: Lycopodium): Currently at {p_curr} hectares out of a {TARGETS['plant']} hectare target. Change in selected window: {p_delta} ha.
2. Access Road Development (Contractor: BCM): Currently at {r_curr} kilometers out of a {TARGETS['road']} km target. Change in selected window: {r_delta} km.
3. Genji Resettlement Village Construction (Contractor: Dashen): Currently at {int(g_curr)} housing units out of a {TARGETS['genji']} unit target. Change in selected window: {int(g_delta)} units.

Write a concise, highly professional 2-3 paragraph management summary. Do not include introductory or concluding pleasantries. Focus strictly on operational pace, milestone achievements against the targets, and data-driven insights derived directly from the optical telemetry provided. Format with clear headings if necessary.
"""

if st.button("Generate Management Report", type="primary"):
    with st.spinner("Initiating LLM analysis..."):
        try:
            # Securely fetch API key from Streamlit's secrets manager
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            
            # Using Gemini 1.5 Flash (the currently active optimal fast tier for text generation)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            st.success("Briefing Generated Successfully")
            st.markdown(f"> {response.text}")
            
        except FileNotFoundError:
            st.error("Error: Local Streamlit secrets file not found. Ensure you configured your API key.")
        except KeyError:
            st.error("Error: GEMINI_API_KEY not found in Streamlit Secrets. Please configure it in your Streamlit Cloud dashboard.")
        except Exception as e:
            st.error(f"An error occurred while communicating with the Gemini API: {e}")
