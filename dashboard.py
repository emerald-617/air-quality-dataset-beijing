# === IMPORT LIBRARY ==================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium


# === PAGE CONFIG =====================================================
st.set_page_config(
    page_title="Beijing Air Quality Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .card {
        background-color: #f5f5f5;
        padding: 20px;
        border-radius: 15px;
        border-top: 5px solid;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .title  { font-size: 14px; color: #555; }
    .value  { font-size: 32px; font-weight: bold; }
    .desc   { font-size: 13px; color: gray; }
    .delta  {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("Dashboard Beijing Air Quality")


# === CONSTANTS =======================================================
AQI_BINS   = [0, 50, 100, 150, 200, 300, 600]
AQI_LABELS = [
    "Excellent", "Good", "Lightly Polluted",
    "Moderately Polluted", "Heavily Polluted", "Severely Polluted",
]
AQI_COLORS  = ["#328b36", "#66bb6a", "#ffa726", "#e35c5a", "#ab47bc", "#941212"]
AQI_PALETTE = dict(zip(AQI_LABELS, AQI_COLORS))

POLLUTANTS    = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"]
WEATHER_VARS  = ["TEMP", "PRES", "DEWP", "RAIN", "WSPM"]

SEASON_MAPPING = {
    3: "Spring", 4: "Spring",  5: "Spring",
    6: "Summer", 7: "Summer",  8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
    12: "Winter", 1: "Winter",  2: "Winter",
}

STATION_COORDS = {
    "Aotizhongxin":  (39.982, 116.397),
    "Changping":     (40.217, 116.231),
    "Dingling":      (40.292, 116.220),
    "Dongsi":        (39.929, 116.417),
    "Guanyuan":      (39.933, 116.339),
    "Gucheng":       (39.914, 116.184),
    "Huairou":       (40.357, 116.628),
    "Nongzhanguan":  (39.937, 116.461),
    "Shunyi":        (40.127, 116.655),
    "Tiantan":       (39.886, 116.407),
    "Wanliu":        (39.987, 116.306),
    "Wanshouxigong": (39.878, 116.352),
}


# === HELPERS =========================================================
@st.cache_data
def load_data():
    df_all     = pd.read_csv("data/df_all.csv",               parse_dates=["date"])
    df_daily   = pd.read_csv("data/df_agregasi.csv",          parse_dates=["date"])
    df_monthly = pd.read_csv("data/df_monthly_station.csv",   parse_dates=["year_month"])
    df_all["season"] = df_all["month"].map(SEASON_MAPPING)
    return df_all, df_daily, df_monthly


def filter_daily(df: pd.DataFrame, start_date, end_date, stations: list) -> pd.DataFrame:
    """Filter df_daily by date range and station list."""
    mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
    df = df.loc[mask]
    if "Semua" not in stations:
        df = df[df["station"].isin(stations)]
    return df


def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def get_aqi_category(aqi: float) -> str:
    return str(pd.cut([aqi], bins=AQI_BINS, labels=AQI_LABELS, include_lowest=True)[0])


def get_aqi_style(aqi: float) -> dict:
    category = get_aqi_category(aqi)
    color = AQI_PALETTE[category]
    return {
        "border":    f"border-top-color: {color};",
        "delta_text": f"color: {color};",
        "delta_bg":   f"background-color: {hex_to_rgba(color)};",
        "label":      category,
    }


def aqi_color(val: float) -> str:
    thresholds = list(zip(AQI_BINS[1:], AQI_COLORS))
    for threshold, color in thresholds:
        if val <= threshold:
            return color
    return AQI_COLORS[-1]


def render_card(title, value, desc, delta_text, border_color, delta_color) -> str:
    return f"""
    <div class="card" style="border-top-color:{border_color};">
        <div class="title">{title}</div>
        <div class="value">{value}</div>
        <div class="desc">{desc}</div>
        <div class="delta" style="color:{delta_color}; background:{hex_to_rgba(delta_color)};">
            {delta_text}
        </div>
    </div>
    """


# === LOAD DATA =======================================================
df_all, df_daily, df_monthly = load_data()


# === SIDEBAR — FILTER ================================================
with st.sidebar:
    st.subheader("FILTER")

    min_date = df_daily["date"].min().date()
    max_date = df_daily["date"].max().date()

    date_range = st.date_input(
        label="Rentang Waktu",
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date],
    )

    # Guard: user may not have finished picking both dates
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0] if date_range else min_date

    all_stations  = df_daily["station"].unique().tolist()
    station_opts  = ["Semua"] + all_stations
    selected_stations = st.multiselect("Stasiun", station_opts, default="Dongsi")

    st.caption("Air Quality Dataset")


# === APPLY FILTER ====================================================
df_filtered = filter_daily(df_daily, start_date, end_date, selected_stations)


# === TABS ============================================================
tab_ringkasan, tab_tren, tab_peta = st.tabs(["Ringkasan", "Tren Waktu", "Peta"])


# === TAB 1 : RINGKASAN ===============================================
with tab_ringkasan:
    st.subheader("Indikator Utama")

    total_days            = len(df_filtered)
    avg_aqi               = df_filtered["AQI"].mean().round(2) if total_days else 0
    high_days             = int((df_filtered["AQI"] > 150).sum())
    low_days              = int((df_filtered["AQI"] <= 150).sum())
    high_pct              = high_days / total_days if total_days else 0
    low_pct               = low_days  / total_days if total_days else 0

    style = get_aqi_style(avg_aqi)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="card" style="{style['border']}">
            <div class="title">Rata-rata AQI</div>
            <div class="value">{avg_aqi}</div>
            <div class="desc">skala 0–500</div>
            <div class="delta" style="{style['delta_text']} {style['delta_bg']}">{style['label']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(
            render_card(
                "Hari Polusi Tinggi", high_days,
                "hari dengan AQI > 150", f"{high_pct:.2%} dari total hari",
                "#e53e3e", "#e53e3e",
            ), unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            render_card(
                "Hari Polusi Rendah", low_days,
                "hari dengan AQI ≤ 150", f"{low_pct:.2%} dari total hari",
                "#38a169", "#38a169",
            ), unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Tren AQI Bulanan ---
    st.subheader("Tren AQI Bulanan")
    st.caption("Rata-rata berdasarkan filter aktif")

    ts_df = df_filtered.copy()
    ts_df["time"] = ts_df["date"].dt.to_period("M").dt.to_timestamp()
    ts_df = ts_df.groupby("time")["AQI"].mean().reset_index().sort_values("time")

    CHART_HEIGHT = 320

    fig, ax = plt.subplots(figsize=(12, CHART_HEIGHT / 96))   # 96 dpi default
    ax.plot(ts_df["time"], ts_df["AQI"], linewidth=1.4, color="steelblue")
    ax.set_ylabel("AQI")
    ax.set_xlabel("Tanggal")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.subheader("Distribusi Kategori AQI")
    st.caption("Proporsi hari per kategori")

    df_filtered["AQI_cat"] = pd.cut(
        df_filtered["AQI"], bins=AQI_BINS,
        labels=AQI_LABELS, right=True, include_lowest=True,
    )
    dist = (
        df_filtered["AQI_cat"]
        .value_counts(normalize=True)
        .mul(100)
        .reindex(AQI_LABELS, fill_value=0)
        .round(1)
        .reset_index()
    )
    dist.columns = ["Kategori", "Persentase"]
    dist = dist[dist["Persentase"] > 0]
    dist["Kategori"] = pd.Categorical(dist["Kategori"], categories=AQI_LABELS, ordered=True)
    dist = dist.sort_values("Kategori")


    # --- donut ---
    h_in   = CHART_HEIGHT / 96
    fig_pie, (ax_pie, ax_leg) = plt.subplots(
        1, 2, figsize=(h_in * 2, h_in),
        gridspec_kw={"width_ratios": [1, 1]}
    )
    ax_pie.pie(
        dist["Persentase"],
        colors=[AQI_PALETTE[k] for k in dist["Kategori"]],
        startangle=90,
        wedgeprops=dict(width=0.45),
    )
    ax_pie.text(0, 0, "Kategori\nAQI", ha="center", va="center",
                fontsize=9, fontweight="bold", color="#333")

    ax_leg.axis("off")
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=AQI_PALETTE[row["Kategori"]],
                    markersize=9, label=f"{row['Kategori']}  {row['Persentase']}%")
        for _, row in dist.iterrows()
    ]
    ax_leg.legend(
        handles=legend_handles,
        loc="center",
        frameon=False,
        fontsize=8.5,
        handletextpad=0.5,
        labelspacing=0.7,
    )

    fig_pie.tight_layout(pad=0.5)
    st.pyplot(fig_pie)
    plt.close(fig_pie)


# === TAB 2 : TREN WAKTU ==============================================
with tab_tren:
    st.title("📈 Time Series Plot")

    col1, col2 = st.columns([2, 1])
    with col1:
        ts_vars = st.multiselect(
            "Variabel yang ditampilkan",
            options=POLLUTANTS + WEATHER_VARS + ["AQI"],
            default=["AQI", "PM2.5"],
        )
    with col2:
        granularity = st.selectbox("Granularitas", ["Daily", "Monthly", "Yearly"])

    if not ts_vars:
        st.warning("Pilih minimal satu variabel.")
        st.stop()

    # Gunakan df_filtered (sudah terfilter tanggal & stasiun)
    ts_src = df_filtered.copy()

    available_vars = [v for v in ts_vars if v in ts_src.columns]

    if granularity == "Daily":
        ts_df = ts_src.groupby("date")[available_vars].mean().reset_index().rename(columns={"date": "time"})
    elif granularity == "Monthly":
        ts_src["time"] = ts_src["date"].dt.to_period("M").dt.to_timestamp()
        ts_df = ts_src.groupby("time")[available_vars].mean().reset_index()
    else:
        ts_src["time"] = ts_src["date"].dt.to_period("Y").dt.to_timestamp()
        ts_df = ts_src.groupby("time")[available_vars].mean().reset_index()

    ts_df = ts_df.sort_values("time")

    n_vars = len(available_vars)
    fig, axes = plt.subplots(n_vars, 1, figsize=(12, 3 * n_vars), sharex=True)
    if n_vars == 1:
        axes = [axes]

    for ax, var in zip(axes, available_vars):
        ax.plot(ts_df["time"], ts_df[var], linewidth=1.2, color="steelblue")
        ax.set_ylabel(var)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Tanggal")
    fig.suptitle(f"Time Series — {granularity}", fontsize=13, y=1.01)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close()


# === TAB 3 : PETA ====================================================
with tab_peta:
    st.title("🗺️ Peta Stasiun")

    map_metric = st.selectbox(
        "Pilih metrik yang ditampilkan pada peta",
        ["AQI"] + POLLUTANTS + WEATHER_VARS,
    )

    # Agregasi metric per stasiun dari df_filtered
    metric_col = map_metric if map_metric in df_filtered.columns else "AQI"
    station_metric = (
        df_filtered.groupby("station")[metric_col]
        .mean()
        .reset_index()
        .rename(columns={metric_col: "value"})
    )

    # Tambahkan koordinat
    station_metric["lat"] = station_metric["station"].map(lambda x: STATION_COORDS.get(x, (np.nan, np.nan))[0])
    station_metric["lon"] = station_metric["station"].map(lambda x: STATION_COORDS.get(x, (np.nan, np.nan))[1])
    map_df = station_metric.dropna(subset=["lat", "lon", "value"])

    # Folium map
    center_lat = map_df["lat"].mean()
    center_lon = map_df["lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")

    for _, row in map_df.iterrows():
        val    = row["value"]
        color  = aqi_color(val) if metric_col == "AQI" else "steelblue"
        radius = max(6, min(30, val / 8)) if metric_col == "AQI" else 10
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color="black", weight=0.8,
            fill=True, fill_color=color, fill_opacity=0.75,
            tooltip=folium.Tooltip(f"<b>{row['station']}</b><br>{metric_col}: {val:.1f}"),
        ).add_to(m)

    if metric_col == "AQI":
        legend_html = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                    background:white;padding:10px;border-radius:8px;
                    border:1px solid #ccc;font-size:12px;">
            <b>AQI Category</b><br>
        """
        for label, color in zip(AQI_LABELS, AQI_COLORS):
            legend_html += (
                f'<span style="background:{color};display:inline-block;'
                f'width:14px;height:14px;margin-right:5px;border-radius:2px;"></span>'
                f'{label}<br>'
            )
        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width=900, height=520)

    st.subheader(f"Rata-rata {metric_col} per Stasiun")
    st.dataframe(
        map_df[["station", "value"]]
        .rename(columns={"value": f"Avg {metric_col}"})
        .sort_values(f"Avg {metric_col}", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
    )

st.caption('Copyright © Vini Emeralda 2026')