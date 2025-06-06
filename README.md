# FleetLab Safety Dashboard

🚐 **FleetLab Safety Estimation & Risk Reduction Tool**

---

## 🔎 Overview

FleetLab Safety Dashboard is a decision-support tool for school transportation planners, districts, and stakeholders to analyze:

- Stop-level safety risks
- Community-level transportation risk
- System-wide injury reduction potential when adopting FleetLab vans
- Side-by-side comparisons of current fleet vs FleetLab scenarios

The tool leverages both quantitative SES (Stop Evaluation Score) scoring and community-wide transportation risk models to support safer and more cost-effective school transportation planning.

---

## 🌐 Live Application

**👉 [Launch FleetLab Safety Dashboard](https://fleetlab-dashboard-gow8jtusa9pvzrzyn9wg9a.streamlit.app)**

---

## ⚙️ Core Features

### 1️⃣ **File Upload**

- Upload your own stop data (`CSV`) with required columns.
- Or, use provided sample data to explore the tool.

### 2️⃣ **Automatic Geocoding**

- Uses Google Maps API to geocode uploaded stop addresses into latitude and longitude.
- Automatically handles missing locations.

### 3️⃣ **Auto-filled Safety Factors**

- If missing, auto-generates:
  - Traffic Risk (`Traffic Risk (T)`)
  - Construction Risk (`Construction Risk (C)`)
  - U-Turn Required (`U-Turn Required (U)`) (estimates based on routing heuristics)

### 4️⃣ **Customizable SES Weights**

- Customize the Stop Evaluation Score weights for:
  - Visibility
  - Lighting
  - Traffic
  - Pedestrian Safety
  - Sidewalk Quality
  - Construction Risk
  - U-Turn Risk

### 5️⃣ **Stop-Level Safety Scoring**

- Calculates SES Score per stop using weighted safety factors.
- Allows mode selection for each stop (`Car`, `School Bus`, `FleetLab Van`).
- Provides **Best Mode Recommendation** for each stop.

### 6️⃣ **Fleet Adoption Risk Analysis**

- Allows users to simulate switching % of the fleet to FleetLab vans.
- Calculates total expected system-wide injury risk.
- Visualizes risk reduction vs current baseline.

### 7️⃣ **Community Risk Estimation**

- Aggregates risk factors:
  - Teen drivers %
  - Van adoption %
  - Average SES score
- Provides simple risk category (`Low`, `Medium`, `High`) and expected incidents.

### 8️⃣ **Interactive Map Visualization**

- Interactive Folium map showing each stop.
- Map popups include:
  - Current SES
  - Current Mode
  - Best Mode recommendation
  - Best achievable SES score

### 9️⃣ **Data Table + SES Bar Chart**

- Full data table of all stops, including Best Mode.
- Horizontal SES bar chart for easy visual review.

---

## 🗂️ Repository Structure

```bash
fleetlab_dashboard/
├── streamlit_app.py        # Main Streamlit app code
├── sample_stops.csv        # Sample stop-level data file
├── transportation_mode_risk.csv  # Base transportation mode injury risk data
├── requirements.txt        # Package dependencies
└── README.md               
