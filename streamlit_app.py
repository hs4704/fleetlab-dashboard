import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import googlemaps
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="FleetLab Safety Dashboard v1.7", layout="wide")

st.title("\U0001F696 FleetLab Safety Estimation Dashboard")

# === FILE UPLOAD ===
st.sidebar.header("Upload Your Stop File")
uploaded_file = st.sidebar.file_uploader("Upload CSV with Stop Data", type="csv")

with st.spinner("Loading stop data..."):
    if uploaded_file:
        df_stops = pd.read_csv(uploaded_file)
        st.sidebar.success("✅ File uploaded successfully!")
    else:
        df_stops = pd.read_csv("sample_stops.csv")
        st.sidebar.warning("📄 Using default sample_stops.csv")

# === GOOGLE MAPS GEOCODING ===
gmaps = googlemaps.Client(key=st.secrets["google"]["maps_api_key"])

@st.cache_data(show_spinner="Geocoding addresses...")
def geocode_addresses(addresses):
    latitudes, longitudes = [], []
    for address in addresses:
        try:
            geocode = gmaps.geocode(address)
            if geocode:
                location = geocode[0]['geometry']['location']
                latitudes.append(location["lat"])
                longitudes.append(location["lng"])
            else:
                latitudes.append(None)
                longitudes.append(None)
        except:
            latitudes.append(None)
            longitudes.append(None)
        time.sleep(0.2)
    return latitudes, longitudes

# === AUTO FILL MISSING FACTORS ===
def autofill_missing_fields(df):
    for idx, row in df.iterrows():
        address = row['Address']
        if 'Traffic Risk (T)' not in df.columns or pd.isna(row.get('Traffic Risk (T)')):
            df.at[idx, 'Traffic Risk (T)'] = 0.5
        if 'U-Turn Required (U)' not in df.columns or pd.isna(row.get('U-Turn Required (U)')):
            try:
                directions = gmaps.directions("school address", address, mode="driving")
                u_turn = 0
                for leg in directions:
                    for step in leg['legs'][0]['steps']:
                        if step.get('maneuver') in ['uturn-left', 'uturn-right']:
                            u_turn = 1
                df.at[idx, 'U-Turn Required (U)'] = u_turn
            except:
                df.at[idx, 'U-Turn Required (U)'] = 0
        if 'Construction Risk (C)' not in df.columns or pd.isna(row.get('Construction Risk (C)')):
            df.at[idx, 'Construction Risk (C)'] = 0.2
    return df

if "lat" not in df_stops.columns or "lon" not in df_stops.columns:
    if "Address" in df_stops.columns:
        lats, lons = geocode_addresses(df_stops["Address"])
        df_stops["lat"] = lats
        df_stops["lon"] = lons
    else:
        st.warning("📍 No Address column found, and no lat/lon available.")

with st.spinner("Auto-generating missing safety factors..."):
    df_stops = autofill_missing_fields(df_stops)

# === SES WEIGHT SLIDERS ===
st.sidebar.header("Customize SES Weights")
weights = {
    "V": st.sidebar.slider("Visibility", 0.0, 1.0, 0.25, 0.05),
    "L": st.sidebar.slider("Lighting", 0.0, 1.0, 0.15, 0.05),
    "T": st.sidebar.slider("Traffic Risk", 0.0, 1.0, 0.25, 0.05),
    "P": st.sidebar.slider("Pedestrian Safety", 0.0, 1.0, 0.2, 0.05),
    "S": st.sidebar.slider("Sidewalk Quality", 0.0, 1.0, 0.1, 0.05),
    "C": st.sidebar.slider("Construction Risk", 0.0, 1.0, 0.05, 0.05),
    "U": st.sidebar.slider("U-Turn Required", 0.0, 1.0, 0.05, 0.05)
}

# === COMPACT MODE SELECTOR ===
st.sidebar.header("Transportation Mode Assignment")
stop_list = df_stops["Stop Name"].tolist()
selected_stop = st.sidebar.selectbox("Select Stop", stop_list)
mode_options = ["Car", "School Bus", "FleetLab Van"]
selected_mode = st.sidebar.selectbox("Assign Mode", mode_options)
if "Selected Mode" not in df_stops.columns:
    df_stops["Selected Mode"] = "Car"
df_stops.loc[df_stops["Stop Name"] == selected_stop, "Selected Mode"] = selected_mode

# === MODE MODIFIERS ===
mode_modifiers = {
    "Car": {"T": 0.1, "U": 0.2, "P": -0.1},
    "School Bus": {"T": -0.1, "U": 0.0, "P": 0.0},
    "FleetLab Van": {"T": -0.2, "U": -0.2, "P": 0.2}
}

# === SES SCORE CALCULATION ===
def compute_ses(row):
    mods = mode_modifiers.get(row["Selected Mode"], {})
    adjusted = {
        "V": row["Visibility (V)"],
        "L": row["Lighting (L)"],
        "T": max(min(row["Traffic Risk (T)"] + mods.get("T", 0), 1), 0),
        "P": max(min(row["Pedestrian Safety (P)"] + mods.get("P", 0), 1), 0),
        "S": row["Sidewalk Quality (S)"],
        "C": row["Construction Risk (C)"],
        "U": max(min(row["U-Turn Required (U)"] + mods.get("U", 0), 1), 0)
    }
    return (
        weights["V"] * adjusted["V"] +
        weights["L"] * adjusted["L"] +
        weights["T"] * (1 - adjusted["T"]) +
        weights["P"] * adjusted["P"] +
        weights["S"] * (1 - adjusted["S"]) +
        weights["C"] * (1 - adjusted["C"]) +
        weights["U"] * (1 - adjusted["U"])
    )

df_stops["SES Score"] = df_stops.apply(compute_ses, axis=1)

def classify_ses(score):
    if score > 0.7:
        return "Safe"
    elif score >= 0.5:
        return "Acceptable"
    else:
        return "Unsafe"

df_stops["Safety Rating"] = df_stops["SES Score"].apply(classify_ses)

# === COMMUNITY RISK ===
st.subheader("\U0001F3EB Community Risk Estimation")
teen_rate = st.slider("Teen Drivers %", 0.0, 1.0, 0.4, 0.05)
van_adoption = st.slider("FleetLab Van Adoption %", 0.0, 1.0, 0.2, 0.05)
students = st.slider("Total District Students", 100, 10000, 2000, 100)

avg_ses = df_stops["SES Score"].mean()
community_score = (teen_rate * 5) - (van_adoption * 3) - (avg_ses * 2)
category = "✅ Low Risk" if community_score <= -0.5 else "🟡 Medium Risk" if community_score <= 1 else "❌ High Risk"
estimated_incidents = max(community_score, 0) * students / 1000

st.write(f"**Community Score:** {community_score:.2f} → {category}")
st.write(f"Estimated annual incidents: {estimated_incidents:.1f} per {students} students")

# === MAP ===
st.subheader("\U0001F30D Stop Safety Map")
if "lat" in df_stops.columns and "lon" in df_stops.columns:
    m = folium.Map(location=[df_stops["lat"].mean(), df_stops["lon"].mean()], zoom_start=13)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df_stops.iterrows():
        color = "green" if row["Safety Rating"] == "Safe" else "orange" if row["Safety Rating"] == "Acceptable" else "red"
        popup_html = f"""
            <b>{row['Stop Name']}</b><br>
            SES: {row['SES Score']:.2f}<br>
            Safety Rating: {row['Safety Rating']}<br>
            Selected Mode: {row['Selected Mode']}<br>
        """
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=500)
        ).add_to(marker_cluster)

    st_folium(m, width=900, height=600)
else:
    st.warning("📍 No latitude/longitude data available to render map.")
