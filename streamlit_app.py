import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# === PAGE CONFIG ===
st.set_page_config(page_title="FleetLab Safety Dashboard", layout="wide")

st.title("🚐 FleetLab Safety Estimation Dashboard")

# === FILE UPLOAD ===
st.sidebar.header("Upload Your Stop File")
uploaded_file = st.sidebar.file_uploader("Upload CSV with Stop Data", type="csv")
if uploaded_file:
    df_stops = pd.read_csv(uploaded_file)
    st.sidebar.success("✅ File uploaded successfully!")
else:
    df_stops = pd.read_csv("sample_stops.csv")
    st.sidebar.warning("📄 Using default sample_stops.csv")

df_transport = pd.read_csv("transportation_mode_risk.csv")

# === COMMUNITY RISK SLIDERS ===
st.sidebar.header("Community Risk Inputs")
teen_rate = st.sidebar.slider("Teen Drivers (%)", 0.0, 1.0, 0.4, 0.05)
van_adoption = st.sidebar.slider("FleetLab Van Adoption (%)", 0.0, 1.0, 0.2, 0.05)
avg_ses = st.sidebar.slider("Avg Stop SES Score", 0.0, 1.0, 0.7, 0.05)
students = st.sidebar.slider("Total Students in District", 100, 10000, 2000, 100)

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

# === TRANSPORT RISK CALCULATION ===
df_transport["Switch_%"] = df_transport["Base_%"]
df_transport.loc[df_transport["Mode"] == "FleetLab Van", "Switch_%"] = van_adoption
other_modes = df_transport[df_transport["Mode"] != "FleetLab Van"].copy()
rescale = 1 - van_adoption
other_modes["Switch_%"] = (other_modes["Base_%"] / other_modes["Base_%"].sum()) * rescale
df_transport.update(other_modes)

df_transport["Base_Risk"] = df_transport["Risk_per_Million"] * df_transport["Base_%"]
df_transport["Switch_Risk"] = df_transport["Risk_per_Million"] * df_transport["Switch_%"]

# === TRANSPORTATION RISK CHART ===
st.subheader("📊 Transportation Mode Risk")
st.dataframe(df_transport[["Mode", "Base_Risk", "Switch_Risk"]])
fig, ax = plt.subplots(figsize=(8, 5))
df_transport.plot(x="Mode", y=["Base_Risk", "Switch_Risk"], kind="bar", ax=ax,
                  color=["#FFA07A", "#90EE90"])
plt.title("Expected Injuries per 1M Students")
plt.ylabel("Risk Contribution")
plt.xticks(rotation=45)
st.pyplot(fig)

# === INSIGHT SUMMARY ===
base = df_transport["Base_Risk"].sum()
switch = df_transport["Switch_Risk"].sum()
drop = base - switch
percent = (drop / base) * 100

st.markdown("## 📉 System Risk Insight")
st.success(f"Current expected risk: **{base:.2f} per 1M students**")
st.success(f"After switching to FleetLab: **{switch:.2f}**, a reduction of **{drop:.2f}** ({percent:.1f}%)")

# === COMMUNITY RISK CALC ===
def calc_community_risk(teen, van, ses, w1=5, w2=3, w3=2):
    return (teen * w1) - (van * w2) - (ses * w3)

score = calc_community_risk(teen_rate, van_adoption, avg_ses)
category = "✅ Low Risk" if score <= -0.5 else "🟡 Medium Risk" if score <= 1 else "❌ High Risk"
expected = max(score, 0) * students / 1000

st.subheader("🏫 Community Risk Estimation")
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

df_stops["SES Score"] = df_stops.apply(compute_ses, axis=1)

def classify_ses(score):
    if score > 0.7:
        return "Safe"
    elif score >= 0.5:
        return "Acceptable"
    else:
        return "Unsafe"

df_stops["Safety Rating"] = df_stops["SES Score"].apply(classify_ses)

# === MAP VIEW ===
st.subheader("🌍 Stop Safety Map")

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
                popup=(f"<b>{row['Stop Name']}</b><br>SES: {row['SES Score']:.2f}<br>Rating: {row['Safety Rating']}")
            ).add_to(marker_cluster)
    st_folium(m, width=800)
else:
    st.warning("📍 Map data not available (lat/lon columns missing).")

# === SES TABLE + BAR CHART ===
st.subheader("🚏 Stop Safety Table")
st.dataframe(df_stops[["Stop Name", "SES Score", "Safety Rating"]])

fig2, ax2 = plt.subplots(figsize=(10, 6))
df_sorted = df_stops.sort_values("SES Score")
colors = df_sorted["Safety Rating"].map({
    "Safe": "green", "Acceptable": "orange", "Unsafe": "red"
})
ax2.barh(df_sorted["Stop Name"], df_sorted["SES Score"], color=colors)
ax2.axvline(0.7, linestyle="--", color="green", label="Safe Threshold (0.7)")
ax2.axvline(0.5, linestyle="--", color="orange", label="Acceptable Threshold (0.5)")
plt.title("Stop Safety Scores (SES)")
plt.xlabel("SES Score")
plt.legend(loc="lower right")
plt.tight_layout()
st.pyplot(fig2)
