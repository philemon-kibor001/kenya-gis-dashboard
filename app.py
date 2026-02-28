# app.py
import os
import random

import pandas as pd
import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="Kenya GIS Dashboard", page_icon="🗺️", layout="wide")

st.title("🗺️ Kenya GIS Dashboard")
st.caption("Built by Philemon Kibor – GIS & AI Specialist")

# -----------------------------
# Create demo data (GeoJSON) if missing
# -----------------------------
os.makedirs("data", exist_ok=True)
geojson_path = "data/points.geojson"

def create_demo_geojson(path: str, n: int = 120):
    random.seed(42)

    # Nairobi-ish center (change if you want)
    center_lat, center_lon = -1.286389, 36.817223

    categories = ["Residential", "Commercial", "Industrial", "Public"]
    wards = ["Kilimani", "Westlands", "CBD", "South B", "Eastlands"]

    rows = []
    for i in range(n):
        lat = center_lat + random.uniform(-0.08, 0.08)
        lon = center_lon + random.uniform(-0.10, 0.10)
        cat = random.choice(categories)
        ward = random.choice(wards)
        score = round(random.uniform(0, 100), 2)

        rows.append(
            {
                "id": f"P{i:03d}",
                "category": cat,
                "ward": ward,
                "score": score,
                "geometry": Point(lon, lat),
            }
        )

    gdf_demo = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf_demo.to_file(path, driver="GeoJSON")

if not os.path.exists(geojson_path):
    create_demo_geojson(geojson_path)

# -----------------------------
# Load data
# -----------------------------
gdf = gpd.read_file(geojson_path)
if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:4326")
elif gdf.crs.to_string() != "EPSG:4326":
    gdf = gdf.to_crs("EPSG:4326")

# Ensure required columns exist
for col, default in [("category", "Unknown"), ("ward", "Unknown"), ("score", 0)]:
    if col not in gdf.columns:
        gdf[col] = default

# -----------------------------
# Sidebar filters (with Select All / Clear)
# -----------------------------
st.sidebar.header("Filters")

all_cats = sorted(gdf["category"].astype(str).unique().tolist())
all_wards = sorted(gdf["ward"].astype(str).unique().tolist())

if "selected_categories" not in st.session_state:
    st.session_state.selected_categories = all_cats
if "selected_wards" not in st.session_state:
    st.session_state.selected_wards = all_wards

b1, b2 = st.sidebar.columns(2)
if b1.button("Select all", use_container_width=True):
    st.session_state.selected_categories = all_cats
    st.session_state.selected_wards = all_wards
if b2.button("Clear", use_container_width=True):
    st.session_state.selected_categories = []
    st.session_state.selected_wards = []

selected_categories = st.sidebar.multiselect(
    "Category",
    options=all_cats,
    default=st.session_state.selected_categories,
)

selected_wards = st.sidebar.multiselect(
    "Ward",
    options=all_wards,
    default=st.session_state.selected_wards,
)

score_min = float(pd.to_numeric(gdf["score"], errors="coerce").min())
score_max = float(pd.to_numeric(gdf["score"], errors="coerce").max())
score_range = st.sidebar.slider(
    "Score range",
    min_value=score_min,
    max_value=score_max,
    value=(score_min, score_max),
)

filtered = gdf[
    (gdf["category"].astype(str).isin(selected_categories))
    & (gdf["ward"].astype(str).isin(selected_wards))
    & (pd.to_numeric(gdf["score"], errors="coerce").between(score_range[0], score_range[1]))
].copy()

# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Points", f"{len(filtered):,}")
k2.metric("Categories", f"{filtered['category'].nunique():,}")
k3.metric("Wards", f"{filtered['ward'].nunique():,}")
k4.metric("Avg Score", f"{pd.to_numeric(filtered['score'], errors='coerce').mean():.1f}" if len(filtered) else "—")

# -----------------------------
# Layout: Map + Analytics
# -----------------------------
left, right = st.columns([1.35, 1])

# Color palette for categories
palette = {
    "Residential": "#2E86AB",
    "Commercial": "#F18F01",
    "Industrial": "#C73E1D",
    "Public": "#6A4C93",
    "Unknown": "#7A7A7A",
}

with left:
    st.subheader("Interactive Map")

    # Center map on filtered data (fallback to Nairobi)
    if len(filtered) > 0:
        center = [filtered.geometry.y.mean(), filtered.geometry.x.mean()]
    else:
        center = [-1.286389, 36.817223]

    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

    def style_fn(feature):
        cat = str(feature["properties"].get("category", "Unknown"))
        color = palette.get(cat, palette["Unknown"])
        return {"color": color, "weight": 2, "fillColor": color, "fillOpacity": 0.55}

    if len(filtered) > 0:
        folium.GeoJson(
            data=filtered.__geo_interface__,
            name="Filtered Layer",
            style_function=style_fn,
            tooltip=GeoJsonTooltip(
                fields=["id", "category", "ward", "score"],
                aliases=["ID", "Category", "Ward", "Score"],
                localize=True,
                sticky=False,
            ),
        ).add_to(m)
    else:
        folium.Marker(center, popup="No features match filters.").add_to(m)

    # Legend (HTML)
    legend_items = ""
    for cat, color in palette.items():
        # show only categories that exist in data
        if cat in all_cats or cat == "Unknown":
            legend_items += f'<div><span style="color:{color}; font-size:18px;">●</span> {cat}</div>'

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 50px; left: 50px;
        background: white;
        z-index: 9999;
        padding: 10px 12px;
        border: 2px solid #888;
        border-radius: 8px;
        font-size: 14px;
        ">
        <b>Legend</b>
        {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=True).add_to(m)

    st_folium(m, height=560, use_container_width=True)

with right:
    st.subheader("Analytics")

    st.write("**By category**")
    cat_counts = filtered["category"].astype(str).value_counts().reset_index()
    cat_counts.columns = ["category", "count"]
    if len(cat_counts):
        st.bar_chart(cat_counts.set_index("category"))
    else:
        st.info("No data to chart (filters removed all points).")

    st.write("**By ward**")
    ward_counts = filtered["ward"].astype(str).value_counts().reset_index()
    ward_counts.columns = ["ward", "count"]
    if len(ward_counts):
        st.bar_chart(ward_counts.set_index("ward"))

    st.write("**Top rows (filtered)**")
    st.dataframe(filtered.drop(columns=["geometry"], errors="ignore").head(20), use_container_width=True)

st.divider()

# -----------------------------
# Export
# -----------------------------
st.subheader("Export filtered data")

csv_bytes = filtered.drop(columns=["geometry"], errors="ignore").to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download filtered CSV",
    data=csv_bytes,
    file_name="filtered_data.csv",
    mime="text/csv",
)

geojson_bytes = filtered.to_json().encode("utf-8")
st.download_button(
    "⬇️ Download filtered GeoJSON",
    data=geojson_bytes,
    file_name="filtered_points.geojson",
    mime="application/geo+json",
)

st.info(
    "Replace the demo data by putting your own GeoJSON at `data/points.geojson` "
    "(keep CRS as EPSG:4326 for web maps)."
)