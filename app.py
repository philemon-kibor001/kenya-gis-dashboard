import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Kenya GIS Dashboard", layout="wide")

st.title("🗺️ Kenya GIS Dashboard")
st.markdown("Built by Philemon Kibor – GIS & AI Specialist")

# Create demo data if not exists
if not os.path.exists("data"):
    os.makedirs("data")

geojson_path = "data/points.geojson"

if not os.path.exists(geojson_path):
    rows = []
    for i in range(100):
        lat = -1.286 + random.uniform(-0.05, 0.05)
        lon = 36.817 + random.uniform(-0.05, 0.05)
        category = random.choice(["Residential", "Commercial", "Industrial"])
        rows.append({
            "id": i,
            "category": category,
            "value": random.randint(1, 100),
            "geometry": Point(lon, lat)
        })

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf.to_file(geojson_path, driver="GeoJSON")

gdf = gpd.read_file(geojson_path)

# Sidebar filters
st.sidebar.header("Filters")
categories = st.sidebar.multiselect(
    "Category",
    gdf["category"].unique(),
    default=gdf["category"].unique()
)

filtered = gdf[gdf["category"].isin(categories)]

# KPIs
col1, col2 = st.columns(2)
col1.metric("Total Points", len(filtered))
col2.metric("Average Value", round(filtered["value"].mean(), 1))

# Create map
m = folium.Map(location=[-1.286, 36.817], zoom_start=12)

for _, row in filtered.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=6,
        popup=f"Category: {row['category']}<br>Value: {row['value']}",
        fill=True
    ).add_to(m)

st_folium(m, width=700, height=500)

st.markdown("### Data Table")
st.dataframe(filtered.drop(columns="geometry"))