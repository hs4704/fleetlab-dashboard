import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import googlemaps
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="FleetLab Safety Dashboard", layout="wide")

# Optional branding (if logo exists)
# st.image("fleetlab_logo.png", width=200)

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

if "lat" not in df_stops.columns or "lon" not in df_stops.columns:
    if "Address" in df_stops.columns:
        lats, lons = geocode_addresses(df_stops["Address"])
        df_stops["lat"] = lats
        df_stops["lon"] = lons
    else:
        st.warning("⚠️ No Address column found, and no lat/lon available.")

# === COMMUNITY RISK SLIDERS ===
st.sidebar.header("Community Risk Inputs")
teen_rate = st.sidebar.slider("Teen Drivers (%)", 0.0, 1.0, 0.4, 0.05)
van_adoption = st.sidebar.slider("FleetLab Van Adoption (%)", 0.0, 1.0, 0.2, 0.05)
avg_ses = st.sidebar.slider("Avg Stop SES Score", 0.0, 1.0, 0.7, 0.05)
students = st.sidebar.slider("Total Students in District", 100, 10000, 2000, 100)

st.sidebar.divider()

# === SES WEIGHT SLIDERS ===
st.sidebar.header("Customize SES Weights")
weights = {
    "V": st.sidebar.slider("Weight: Visibility", 0.0, 1.0, 0.25, 0.05),
    "L": st.sidebar.slider("Weight: Lighting", 0.0, 1.0, 0.15, 0.05),
    "T": st.sidebar.slider("Weight: Traffic Risk", 0.0, 1.0, 0.25, 0.05),
    "P": st.sidebar.slider("Weight: Pedestrian Safety", 0.0, 1.0, 0.2, 0.05),
    "S": st.sidebar.slider("Weight: Sidewalk Quality", 0.0, 1.0, 0.1, 0.05),
    "C": st.sidebar.slider("Weight: Construction Risk", 0.0, 1.0, 0.05, 0.05),
    "U": st.sidebar.slider("Weight: U-Turn Required", 0.0, 1.0, 0.05, 0.05)
}

st.sidebar.divider()
st.sidebar.markdown(f"**Van Adoption:** {van_adoption*100:.1f}%")

# === TRANSPORTATION MODE MODIFIERS ===
mode_modifiers = {
    "Car": {"T": 0.1, "U": 0.2, "P": -0.1},
    "School Bus": {"T": -0.1, "U": 0.0, "P": 0.0},
    "FleetLab Van": {"T": -0.2, "U": -0.2, "P": 0.2}
}

# === TRANSPORT RISK CALCULATION ===
df_transport = pd.read_csv("transportation_mode_risk.csv")
df_transport["Switch_%"] = df_transport["Base_%"]
df_transport.loc[df_transport["Mode"] == "FleetLab Van", "Switch_%"] = van_adoption
other_modes = df_transport[df_transport["Mode"] != "FleetLab Van"].copy()
rescale = 1 - van_adoption
other_modes["Switch_%"] = (other_modes["Base_%"] / other_modes["Base_%"].sum()) * rescale
df_transport.update(other_modes)
df_transport["Base_Risk"] = df_transport["Risk_per_Million"] * df_transport["Base_%"]
df_transport["Switch_Risk"] = df_transport["Risk_per_Million"] * df_transport["Switch_%"]

with st.expander("\U0001F4CA Transportation Mode Risk", expanded=True):
    st.dataframe(df_transport[["Mode", "Base_Risk", "Switch_Risk"]])
    fig, ax = plt.subplots(figsize=(8, 5))
    df_transport.plot(x="Mode", y=["Base_Risk", "Switch_Risk"], kind="bar", ax=ax, color=["#FFA07A", "#90EE90"])
    plt.title("Expected Injuries per 1M Students")
    plt.ylabel("Risk Contribution")
    plt.xticks(rotation=45)
    st.pyplot(fig)

# === INSIGHT SUMMARY ===
base = df_transport["Base_Risk"].sum()
switch = df_transport["Switch_Risk"].sum()
drop = base - switch
percent = (drop / base) * 100

st.markdown("## \U0001F4C9 System Risk Insight")
st.success(f"Current expected risk: **{base:.2f} per 1M students**")
st.success(f"After switching to FleetLab: **{switch:.2f}**, a reduction of **{drop:.2f}** ({percent:.1f}%)")

# === COMMUNITY RISK CALC ===
def calc_community_risk(teen, van, ses, w1=5, w2=3, w3=2):
    return (teen * w1) - (van * w2) - (ses * w3)

score = calc_community_risk(teen_rate, van_adoption, avg_ses)
category = "✅ Low Risk" if score <= -0.5 else "🟡 Medium Risk" if score <= 1 else "❌ High Risk"
expected = max(score, 0) * students / 1000

with st.expander("\U0001F3EB Community Risk Estimation", expanded=False):
    st.write(f"📊 **Score:** {score:.2f}")
    st.write(f"🧭 **Risk Category:** {category}")
    st.write(f"📈 **Estimated Injuries/Deaths:** {expected:.1f} per {students:,} students")

# === SES SCORE CALCULATION ===
def compute_ses(row):
    return (
        weights["V"] * row["Visibility (V)"] +
        weights["L"] * row["Lighting (L)"] +
        weights["T"] * (1 - row["Traffic Risk (T)"]) +
        weights["P"] * row["Pedestrian Safety (P)"] +
        weights["S"] * (1 - row["Sidewalk Quality (S)"]) +
        weights["C"] * (1 - row["Construction Risk (C)"]) +
        weights["U"] * (1 - row["U-Turn Required (U)"])
    )

def compute_ses_for_mode(row, mode):
    mods = mode_modifiers.get(mode, {})
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

df_stops["Selected Mode"] = df_stops["Stop Name"].apply(
    lambda stop: st.selectbox(f"Select mode for {stop}", ["Car", "School Bus", "FleetLab Van"], key=stop)
)

df_stops["SES Score"] = df_stops.apply(lambda row: compute_ses_for_mode(row, row["Selected Mode"]), axis=1)

def find_best_mode(row):
    scores = {
        mode: compute_ses_for_mode(row, mode)
        for mode in ["Car", "School Bus", "FleetLab Van"]
    }
    best_mode = max(scores, key=scores.get)
    return pd.Series([best_mode, scores[best_mode]], index=["Recommended Mode", "Recommended SES"])

df_stops[["Recommended Mode", "Recommended SES"]] = df_stops.apply(find_best_mode, axis=1)

def classify_ses(score):
    if score > 0.7:
        return "Safe"
    elif score >= 0.5:
        return "Acceptable"
    else:
        return "Unsafe"

df_stops["Safety Rating"] = df_stops["SES Score"].apply(classify_ses)

# === MAP VIEW ===
with st.expander("\U0001F30D Stop Safety Map", expanded=False):
    if "lat" in df_stops.columns and "lon" in df_stops.columns:
        m = folium.Map(location=[df_stops["lat"].mean(), df_stops["lon"].mean()], zoom_start=13)
        marker_cluster = MarkerCluster().add_to(m)

        for _, row in df_stops.iterrows():
            if pd.notna(row["lat"]) and pd.notna(row["lon"]):
                color = "green" if row["Safety Rating"] == "Safe" else "orange" if row["Safety Rating"] == "Acceptable" else "red"
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    popup=(f"<b>{row['Stop Name']}</b><br>"
                           f"SES: {row['SES Score']:.2f}<br>"
                           f"Rating: {row['Safety Rating']}<br>"
                           f"<b>Best Mode:</b> {row['Recommended Mode']}<br>"
                           f"Best SES: {row['Recommended SES']:.2f}<br>"
                           f"Selected Mode: {row['Selected Mode']}<br>")
                ).add_to(marker_cluster)
        st_folium(m, width=800)
    else:
        st.warning("📍 Map data not available (lat/lon columns missing).")

# === SES TABLE + BAR CHART ===
with st.expander("\U0001F68F Stop Safety Table + Chart", expanded=False):
    st.dataframe(df_stops[["Stop Name", "SES Score", "Safety Rating", "Recommended Mode", "Recommended SES"]], use_container_width=True)

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    df_sorted = df_stops.sort_values("SES Score")
    colors = df_sorted["Safety Rating"].map({
        "Safe": "#4CAF50", "Acceptable": "#FFC107", "Unsafe": "#F44336"
    })
    ax2.barh(df_sorted["Stop Name"], df_sorted["SES Score"], color=colors)
    ax2.axvline(0.7, linestyle="--", color="green", label="Safe Threshold (0.7)")
    ax2.axvline(0.5, linestyle="--", color="orange", label="Acceptable Threshold (0.5)")
    plt.title("Stop Safety Scores (SES)")
    plt.xlabel("SES Score")
    plt.legend(loc="lower right")
    plt.tight_layout()
    st.pyplot(fig2)



