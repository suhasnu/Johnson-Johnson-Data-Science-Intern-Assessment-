# Interactive Folium map of employees, workplace, stations and clusters

import folium
from folium.plugins import MarkerCluster

_BIN_COLORS = {
    "0-30": "#2e7d32",   # green
    "30-45": "#f9a825",  # amber
    "45-60": "#ef6c00",  # orange
    "60+": "#c62828",    # red
}


def build_map(df, workplace, stations=None):
    # Return a Folium map. df must contain commute_bin, potential and coords
    center = [workplace["lat"], workplace["lon"]]
    m = folium.Map(location=center, zoom_start=10, tiles="cartodbpositron")

    # Workplace.
    folium.Marker(
        location=center,
        tooltip=workplace["name"],
        popup=workplace["address"],
        icon=folium.Icon(color="blue", icon="briefcase", prefix="fa"),
    ).add_to(m)

    # Nearby HVV stations near the workplace.
    if stations:
        station_group = folium.FeatureGroup(name="Nearby HVV stations")
        for s in stations:
            if s.get("lat") is None:
                continue
            folium.CircleMarker(
                location=[s["lat"], s["lon"]],
                radius=4,
                color="#1565c0",
                fill=True,
                fill_opacity=0.9,
                tooltip=s.get("name"),
            ).add_to(station_group)
        station_group.add_to(m)

    # Employees, grouped by commute-time bin so clusters read clearly.
    for label in ["0-30", "30-45", "45-60", "60+"]:
        sub = df[df["commute_bin"] == label]
        if sub.empty:
            continue
        group = folium.FeatureGroup(name=f"Commute {label} min")
        for _, r in sub.iterrows():
            folium.CircleMarker(
                location=[r["home_lat"], r["home_lon"]],
                radius=5,
                color=_BIN_COLORS[label],
                fill=True,
                fill_opacity=0.7,
                tooltip=(
                    f"{r['area']} | {r['commute_min']:.0f} min | "
                    f"{r['potential']} potential"
                ),
            ).add_to(group)
        group.add_to(m)

    # High-potential users highlighted.
    high = df[df["potential"] == "High"]
    if not high.empty:
        hi_group = folium.FeatureGroup(name="High-potential users")
        cluster = MarkerCluster().add_to(hi_group)
        for _, r in high.iterrows():
            folium.Marker(
                location=[r["home_lat"], r["home_lon"]],
                tooltip=f"{r['area']} | score {r['adoption_score']:.2f}",
                icon=folium.Icon(color="green", icon="star", prefix="fa"),
            ).add_to(cluster)
        hi_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    _add_legend(m)
    return m


def _add_legend(m):
    html = """
    <div style="position: fixed; bottom: 24px; left: 24px; z-index: 9999;
                background: white; padding: 10px 12px; border: 1px solid #ccc;
                border-radius: 6px; font: 12px sans-serif; line-height: 1.6;">
      <b>Commute time</b><br>
      <span style="color:#2e7d32;">&#9679;</span> 0-30 min<br>
      <span style="color:#f9a825;">&#9679;</span> 30-45 min<br>
      <span style="color:#ef6c00;">&#9679;</span> 45-60 min<br>
      <span style="color:#c62828;">&#9679;</span> 60+ min<br>
      <span style="color:#1565c0;">&#9679;</span> HVV station<br>
      &#9733; High-potential user
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))
