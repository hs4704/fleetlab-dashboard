import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === DATA LOAD ===
st.set_page_config(page_title="FleetLab Safety Dashboard", layout="wide")

df_stops = pd.read_csv("sample_stops.csv")
df_transport = pd.read_csv("transportation_mode_risk.csv")

st.title("🚐 FleetLab Safety Estimation Dashboard")

st.sidebar.header("Community Risk Inputs")
teen_rate = st.sidebar.slider("Teen Drivers (%)", 0.0, 1.0, 0.4, 0.05)
van_adoption = st.sidebar.slider("FleetLab Van Adoption (%)", 0.0, 1.0, 0.2, 0.05)
avg_ses = st.sidebar.slider("Avg Stop SES Score", 0.0, 1.0, 0.7, 0.05)
students = st.sidebar.slider("Total Students in District", 100, 10000, 2000, 100)

# Dynamically update Switch_% based on van_adoption slider
df_transport["Switch_%"] = df_transport["Base_%"]  # start from base
df_transport.loc[df_transport["Mode"] == "FleetLab Van", "Switch_%"] = van_adoption

# Recalculate other mode %s proportionally to keep total = 100%
other_modes = df_transport[df_transport["Mode"] != "FleetLab Van"].copy()
rescale = 1 - van_adoption
other_modes["Switch_%"] = (other_modes["Base_%"] / other_modes["Base_%"].sum()) * rescale

df_transport.update(other_modes)

# Calculate Risks
df_transport["Base_Risk"] = df_transport["Risk_per_Million"] * df_transport["Base_%"]
df_transport["Switch_Risk"] = df_transport["Risk_per_Million"] * df_transport["Switch_%"]

st.subheader("📊 Transportation Mode Risk")
st.dataframe(df_transport[["Mode", "Base_Risk", "Switch_Risk"]])
fig, ax = plt.subplots(figsize=(8, 5))
df_transport.plot(x="Mode", y=["Base_Risk", "Switch_Risk"], kind="bar",
                  ax=ax, color=["#FFA07A", "#90EE90"])
plt.title("Expected Injuries per 1M Students")

# --- Risk Summary Text Block ---
base = df_transport["Base_Risk"].sum()
switch = df_transport["Switch_Risk"].sum()
drop = base - switch
percent = (drop / base) * 100

st.markdown("## 📉 System Risk Insight")
st.success(f"Under the current transportation mix, the expected risk is **{base:.2f} injuries per 1M students**.")
st.success(f"After adopting FleetLab vans, risk drops to **{switch:.2f}**, a reduction of **{drop:.2f}**, or **{percent:.1f}%**.")

plt.ylabel("Risk Contribution")
plt.xticks(rotation=45)
st.pyplot(fig)

def calc_community_risk(teen, van, ses, w1=5, w2=3, w3=2):
    return (teen * w1) - (van * w2) - (ses * w3)

def classify(score):
    if score > 1:
        return "❌ High Risk"
    elif score > -0.5:
        return "🟡 Medium Risk"
    else:
        return "✅ Low Risk"

def feedback(score, teen, ses):
    if score > 1:
        return f"⚠️ High risk due to high teen driving ({teen:.0%}) and low stop safety ({ses:.2f})"
    elif score > -0.5:
        return "🟡 Moderate risk. Improve van use or stop SES."
    else:
        return "✅ Low risk. Great job improving safety!"

score = calc_community_risk(teen_rate, van_adoption, avg_ses)
category = classify(score)
expected = max(score, 0) * students / 1000

st.subheader("🏫 Community Risk Estimation")
st.write(f"📊 **Score:** {score:.2f}")
st.write(f"🧭 **Risk Category:** {category}")
st.write(f"📈 **Estimated Injuries/Deaths:** {expected:.1f} per {students:,} students")
st.info(feedback(score, teen_rate, avg_ses))

# === STOP SES SCORE ===
st.subheader("🚏 Stop Safety Scores")

weights = {"V": 0.25, "L": 0.15, "T": 0.25, "P": 0.2, "S": 0.1, "C": 0.05, "U": 0.05}

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
