import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import googlemaps
import time
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="FleetLab Safety Dashboard", layout="wide")

st.title("🚐 FleetLab Safety Estimation Dashboard")

# === LOAD TRANSPORTATION MODE RISK DATA ===
df_transport = pd.read_csv("transportation_mode_risk.csv")

# === CONSTANTS ===
SES_WEIGHTS = {
    'lighting': 0.15,
    'traffic': 0.20,
    'speed': 0.15,
    'sidewalk': 0.15,
    'visibility': 0.15,
    'shoulder': 0.10,
    'crime': 0.10
} #These weights are from fleetlab excel sheet

MODE_MODIFIERS = {
    'Car': 1.0,
    'School Bus': 0.8,
    'FleetLab Van': 0.5
}

SES_THRESHOLDS = {
    'Safe': 85,
    'Acceptable': 70
}
# === HELPERS ===
def normalize_columns(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df

def validate_uploaded_file(df):
    df = normalize_columns(df)
    required_columns = list(SES_WEIGHTS.keys()) + ['address']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"Uploaded file is missing columns: {', '.join(missing_cols)}")
        return None
    return df

@st.cache_data(show_spinner="Geocoding addresses...")
def geocode_addresses(addresses):
    gmaps = googlemaps.Client(key=st.secrets["google"]["maps_api_key"])
    latitudes, longitudes = [], []
    for address in addresses:
        try:
            geocode_result = gmaps.geocode(address)
            if geocode_result:
                loc = geocode_result[0]['geometry']['location']
                latitudes.append(loc['lat'])
                longitudes.append(loc['lng'])
            else:
                latitudes.append(None)
                longitudes.append(None)
        except Exception as e:
            latitudes.append(None)
            longitudes.append(None)
        time.sleep(0.2)
    return latitudes, longitudes

def calculate_ses(row, modifier=1.0):
    raw_score = sum(row[factor] * weight for factor, weight in SES_WEIGHTS.items())
    ses_score = min(raw_score * modifier, 100)
    return ses_score

def assign_ses_category(score):
    if score >= SES_THRESHOLDS['Safe']:
        return "Safe"
    elif score >= SES_THRESHOLDS['Acceptable']:
        return "Acceptable"
    else:
        return "Unsafe"

# INTERACTIVE MAP
def render_map(df):
    m = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        popup = folium.Popup(f"Address: {row['address']}<br>SES: {row['SES']:.1f}<br>Category: {row['SES_Category']}", max_width=300)
        color = {"Safe": "green", "Acceptable": "orange", "Unsafe": "red"}[row['SES_Category']]
        folium.Marker([row['latitude'], row['longitude']], popup=popup, icon=folium.Icon(color=color)).add_to(marker_cluster)
    
    st_folium(m, width=700, height=500)
# SAFETY SUMMARY BAR CHART
def render_safety_summary(df):
    summary = df['SES_Category'].value_counts().reindex(["Safe", "Acceptable", "Unsafe"], fill_value=0)
    st.subheader("Safety Summary")
    st.write(summary)
    summary.plot(kind="bar", color=["green", "orange", "red"])
    st.pyplot(plt)

# Calculate SES scores for each mode globally
def simulate_all_modes(df_original):
    simulation_results = {}
    
    for mode, modifier in MODE_MODIFIERS.items():
        df = df_original.copy()
        df['SES'] = df.apply(lambda row: calculate_ses(row, modifier), axis=1)
        df['SES_Category'] = df['SES'].apply(assign_ses_category)
        summary = df['SES_Category'].value_counts().reindex(["Safe", "Acceptable", "Unsafe"], fill_value=0)
        simulation_results[mode] = summary
    
    return simulation_results

# Comparison bar chart
def render_simulation_chart(simulation_results):
    categories = ["Safe", "Acceptable", "Unsafe"]
    modes = list(MODE_MODIFIERS.keys())
    data = {cat: [simulation_results[mode][cat] for mode in modes] for cat in categories}
    df_sim = pd.DataFrame(data, index=modes)
    
    df_sim.plot(kind="bar", stacked=False, color=["green", "orange", "red"])
    plt.title("Safety Simulation: Mode Comparison")
    plt.ylabel("Number of Stops")
    plt.xlabel("Transportation Mode")
    plt.xticks(rotation=0)
    st.pyplot(plt)
# === FILE UPLOAD ===
st.sidebar.header("Upload Your Stop File")
uploaded_file = st.sidebar.file_uploader("Upload CSV with Stop Data", type="csv")

if uploaded_file:
    df_temp = pd.read_csv(uploaded_file)
    df_stops = validate_uploaded_file(df_temp)
    if df_stops is None:
        st.stop()
    st.sidebar.success("✅ File uploaded successfully!")
else:
    df_temp= pd.read_csv("sample_stops.csv")
    df_stops = validate_uploaded_file(df_temp)
    if df_stops is None:
        st.stop()
    st.sidebar.warning("📄 Using default sample_stops.csv")

# === GEOCODING ===
if 'latitude' not in df_stops.columns or 'longitude' not in df_stops.columns:
    lat, lon = geocode_addresses(df_stops['address'])
    df_stops['latitude'] = lat
    df_stops['longitude'] = lon

# === BATCH MODE OVERRIDE ===
st.sidebar.header("Batch Mode Override")
if 'batch_mode' not in st.session_state:
    st.session_state.batch_mode = list(MODE_MODIFIERS.keys())[0]
st.session_state.batch_mode = st.sidebar.selectbox("Apply Mode to All Stops", list(MODE_MODIFIERS.keys()), index=list(MODE_MODIFIERS.keys()).index(st.session_state.batch_mode))
batch_modifier = MODE_MODIFIERS[st.session_state.batch_mode]

# === SES CALCULATION ===
df_stops['SES'] = df_stops.apply(lambda row: calculate_ses(row, batch_modifier), axis=1)
df_stops['SES_Category'] = df_stops['SES'].apply(assign_ses_category)

# === DISPLAY RESULTS ===
render_map(df_stops)
render_safety_summary(df_stops)

# === DATAFRAME DISPLAY ===
st.subheader("Detailed Stop Data")
st.dataframe(df_stops)

# === SIMULATION MODULE ===
st.header("\U0001F4CA Community-Wide Safety Simulation")
simulation_results = simulate_all_modes(df_stops)
render_simulation_chart(simulation_results)


