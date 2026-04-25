# === IMPORT LIBRARY ==================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import seaborn as sns
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
AQI_LEVELS = [
    (50, "Excellent"),
    (100, "Good"),
    (150, "Lightly Polluted"),
    (200, "Moderately Polluted"),
    (300, "Heavily Polluted"),
]
AQI_COLORS  = ["#328b36", "#66bb6a", "#ffa726", "#e35c5a", "#ab47bc", "#941212"]
AQI_PALETTE = dict(zip(AQI_LABELS, AQI_COLORS))

POLLUTANTS    = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"]
WEATHER_VARS  = ["TEMP", "PRES", "DEWP", "RAIN", "WSPM"]

SEASON_MAPPING = {
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Autumn', 10: 'Autumn', 11: 'Autumn',
    12: 'Winter', 1: 'Winter', 2: 'Winter'
}

SEASON_ORDERS = ['Spring', 'Summer', 'Autumn', 'Winter']

COLS = POLLUTANTS + WEATHER_VARS
COLS.append("AQI")

# === HELPERS =========================================================
@st.cache_data
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
df_daily   = pd.read_csv("data/df_daily_station.csv", parse_dates=["date"])
df_map = pd.read_csv("data/df_map.csv")

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

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0] if date_range else min_date

    all_stations  = df_daily["station"].unique().tolist()
    station_opts  = ["Semua"] + all_stations
    selected_stations = st.multiselect("Stasiun", station_opts, default="Semua")

    if not selected_stations:
        st.warning("Pilih minimal satu stasiun.")
        st.stop()

    granularity = st.selectbox("Granularitas", ["Daily", "Monthly", "Yearly"], index=1)

    st.caption("Air Quality Dataset")


# === APPLY FILTER ====================================================
df_daily_filter = filter_daily(df_daily, start_date, end_date, selected_stations)
df_daily_filter['year_month'] = df_daily_filter['date'].dt.to_period('M')

df_monthly_filtered = (
    df_daily_filter.groupby(['station', 'year_month'])[COLS]
    .mean()
    .reset_index()
)
df_monthly_filtered['year_month'] = df_monthly_filtered['year_month'].dt.to_timestamp()
df_monthly_filtered.rename(columns={'year_month': 'date'}, inplace=True)
df_monthly_filtered = df_monthly_filtered.sort_values(by=["station","date"]).reset_index()
df_monthly_filtered.drop(columns="index", inplace=True)
df_monthly_filtered['month'] = df_monthly_filtered['date'].dt.month

df_monthly_filtered['AQI_cat'] = pd.cut(
    df_monthly_filtered['AQI'],
    bins=AQI_BINS,
    labels=AQI_LABELS,
    right=True   
)

df_yearly_filtered = (
    df_daily_filter.groupby(['station', 'year'])[COLS]
    .mean()
    .reset_index()
)
df_yearly_filtered['date'] = pd.to_datetime(df_yearly_filtered["year"], format="%Y")
df_yearly_filtered['AQI_cat'] = pd.cut(
    df_yearly_filtered['AQI'],
    bins=AQI_BINS,
    labels=AQI_LABELS,
    right=True   
)

if granularity == "Daily":
    df_filter = df_daily_filter.copy()
    gran = "Hari"
    time_group = "date"
elif granularity == "Monthly":
    df_filter = df_monthly_filtered.copy()
    gran = "Bulan"
    time_group = "month"
else:
    df_filter = df_yearly_filtered.copy()
    gran = "Tahun"
    time_group = "year"


# === TABS ====================================================
tab_ringkasan, tab_perbandingan, tab_korelasi = st.tabs(["Ringkasan", "Perbandingan Stasiun", "Analisis Korelasi"])


# === TAB 1 : RINGKASAN ====================================================
with tab_ringkasan:
    # Indikator utamta
    st.subheader("Indikator Utama")

    df_all = (
        df_filter.groupby('date')[COLS]
        .mean()
        .reset_index()
    )
    df_all['month'] = df_all['date'].dt.month
    df_all['year'] = df_all['date'].dt.year

    total_aqi            = len(df_all)
    avg_aqi               = df_all["AQI"].mean().round(2) if total_aqi else 0
    high_aqi             = int((df_all["AQI"] > 150).sum())
    low_aqi              = int((df_all["AQI"] <= 150).sum())
    high_pct              = high_aqi / total_aqi if total_aqi else 0
    low_pct               = low_aqi  / total_aqi if total_aqi else 0

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
                f"{gran} Polusi Tinggi", high_aqi,
                f"{gran} dengan AQI > 150", f"{high_pct:.2%} dari total {gran}",
                "#e53e3e", "#e53e3e",
            ), unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            render_card(
                f"{gran} Polusi Rendah", low_aqi,
                f"{gran} dengan AQI ≤ 150", f"{low_pct:.2%} dari total {gran}",
                "#38a169", "#38a169",
            ), unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Time series tren AQI
    st.subheader(f"Tren AQI {gran}an")
    st.caption("Rata-rata berdasarkan filter aktif")

    ts_df = df_all.copy()
    ts_df = ts_df.sort_values("date").reset_index()
    ts_df.drop(columns="index", inplace=True)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(ts_df["date"], ts_df["AQI"], linewidth=1.4, color="steelblue")
    for j, (level, label) in enumerate(AQI_LEVELS):
        ax.axhline(
            y=level,
            linestyle='--',
            color=AQI_COLORS[j],
            alpha=0.7
        )
    
    ax.set_ylabel("AQI")
    ax.set_xlabel("Waktu")
    ax.grid(True, alpha=0.3)

    legend_lines = [
        Line2D([0], [0], color=AQI_COLORS[i], lw=1.5, linestyle='--', label=label)
        for i, (_, label) in enumerate(AQI_LEVELS)
    ]

    fig.legend(
        handles=legend_lines,
        title="AQI Category",
        loc='lower center',
        bbox_to_anchor=(0.5, -0.02),
        ncol=len(AQI_LEVELS)
    )

    fig.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Distribusi Kategori AQI
    st.subheader("Distribusi Kategori AQI")
    st.caption("Distribusi hari per kategori")

    df_all["AQI_cat"] = pd.cut(
        df_all["AQI"], bins=AQI_BINS,
        labels=AQI_LABELS, right=True, include_lowest=True,
    )
    dist = (
        df_all["AQI_cat"]
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

    h_in   = 3
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

    # Proporsi Kategori AQI
    if granularity != "Daily":
        st.subheader(f"Proporsi Kategori AQI Berdasarkan {gran}")

        prop = pd.crosstab(
            df_all[time_group],
            df_all["AQI_cat"],
            normalize="index"
        ) * 100
        prop = prop.reindex(columns=AQI_LABELS, fill_value=0)
        prop = prop.sort_index()

        fig, ax = plt.subplots(figsize=(12, 6))

        prop.plot(
            kind="bar",
            stacked=True,
            ax=ax,
            color=['green', 'lime', 'orange', 'red', 'purple', 'black']
        )

        ax.set_title(f"Distribusi Kategori AQI ({gran}) (%)")
        ax.set_xlabel("Waktu")
        ax.set_ylabel("Persentase (%)")
        ax.legend(title="AQI Category", bbox_to_anchor=(1.05, 1))

        plt.tight_layout()
        st.pyplot(fig)

    # Data
    st.subheader(f"Data Air Quality {gran}an")
    st.write(df_all)


# === TAB 2 : PERBANDINGAN ANTARSTASIUN ==============================================
with tab_perbandingan:
    # Time series plot per parameter
    st.subheader("Time Series Plot Berdasarkan Parameter")

    ts_vars = st.multiselect(
        "Parameter yang ditampilkan",
        options=POLLUTANTS + WEATHER_VARS + ["AQI"],
        default=["AQI", "PM2.5"],
    )
    if not ts_vars:
        st.warning("Pilih minimal satu parameter.")
        st.stop()

    ts_src = df_filter.copy()

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

    # Time series plot per stasiun
    st.subheader("Time Series Plot AQI Berdasarkan Stasiun")
    st.caption("Filter stasiun pada sidebar")        

    df_stasiun = df_filter.copy()

    stations = df_stasiun["station"].unique()
    n_station = len(stations)

    fig, axes = plt.subplots(n_station, 1, figsize=(15, 6 * n_station), sharex=True)
    axes = axes.flatten()

    for i, station_name in enumerate(stations):

        df_st = df_stasiun[df_stasiun['station'] == station_name]
        
        axes[i].plot(df_st['date'], df_st['AQI'], marker='o')
        axes[i].set_title(f"Time Series Rata-rata Bulanan AQI Stasiun {station_name}")
        axes[i].set_ylabel("AQI")

        for j, (level, label) in enumerate(AQI_LEVELS):
            axes[i].axhline(
                y=level,
                linestyle='--',
                color=AQI_COLORS[j],
                alpha=0.7
            )

    for j in range(len(stations), len(axes)):
        fig.delaxes(axes[j])

    legend_lines = [
        Line2D([0], [0], color=AQI_COLORS[i], lw=1.5, linestyle='--', label=label)
        for i, (_, label) in enumerate(AQI_LEVELS)
    ]

    fig.legend(
        handles=legend_lines,
        title="AQI Category",
        loc='lower center',
        bbox_to_anchor=(0.5, -0.02),
        ncol=len(AQI_LEVELS)
    )

    plt.xlabel("Waktu")
    plt.xticks(rotation=45)
    plt.tight_layout()

    st.pyplot(fig)


    # Perbandingan jumlah hari
    st.subheader("Perbandingan Proporsi Kategori AQI per Stasiun")
    
    fig, axes = plt.subplots(4, 3, figsize=(15, 12))
    axes = axes.flatten()

    df_perbandingan = df_filter.copy()
    df_perbandingan['AQI_cat'] = pd.cut(
        df_perbandingan['AQI'],
        bins=AQI_BINS,
        labels=AQI_LABELS,
        right=True   
    )    

    for i, st_name in enumerate(stations):
        df_st = df_perbandingan[df_perbandingan['station'] == st_name]

        dist = df_st['AQI_cat'].value_counts(normalize=True) * 100
        dist = dist.reindex(AQI_LABELS, fill_value=0)

        max_idx = dist.values.argmax()
        colors_bar1 = ['#D3D3D3'] * len(dist)
        colors_bar1[max_idx] = '#5774B7'

        axes[i].barh(dist.index, dist.values, color=colors_bar1)
        axes[i].set_title(st_name)
        axes[i].tick_params(axis='x', rotation=45)

    for j in range(len(stations), len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    st.pyplot(fig)


    # Peta analisis geospatial
    st.subheader("Peta Beijing")

    metric_col = st.selectbox(
        "Pilih metrik yang ditampilkan pada peta",
        ["AQI"] + ['Perubahan AQI (%)'] + POLLUTANTS + WEATHER_VARS,
    )

    df_map.drop(columns=["AQI_2013", "AQI_2017", "delta_AQI", "pct_change"], inplace=True)
    df_delta = df_map.copy()

    start_year = df_filter['date'].dt.year.min()
    end_year   = df_filter['date'].dt.year.max()
    
    aqi_min = (
        df_filter[df_filter['date'].dt.year == start_year]
        .groupby('station')['AQI']
        .mean()
        .reset_index()
        .rename(columns={'AQI': 'AQI_min'})
    )

    aqi_max = (
        df_filter[df_filter['date'].dt.year == end_year]
        .groupby('station')['AQI']
        .mean()
        .reset_index()
        .rename(columns={'AQI': 'AQI_max'})
    )

    df_delta = df_delta.merge(aqi_min, on='station', how='left')
    df_delta = df_delta.merge(aqi_max, on='station', how='left')

    df_delta['delta_AQI'] = df_delta['AQI_max'] - df_delta['AQI_min']
    df_delta['Perubahan AQI (%)'] = (
        (df_delta['AQI_max'] - df_delta['AQI_min']) /
        df_delta['AQI_min']
    ) * 100

    all_map_metric = ["AQI"] + POLLUTANTS + WEATHER_VARS
    station_metric = (
        df_filter.groupby("station")[all_map_metric]
        .mean()
        .reset_index()
    )

    df_delta = df_delta.merge(station_metric, on='station', how='left')
    
    # Folium map
    cols_map = ["station","lat","lon",metric_col]
    df_map = df_delta[cols_map]
    df_map.dropna(inplace=True)

    center_lat = df_map["lat"].mean()
    center_lon = df_map["lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron")

    for _, row in df_map.iterrows():
        val    = row[metric_col]
        
        #warna
        if metric_col == "AQI":
            map_color = aqi_color(val)
        elif metric_col == metric_col:
            delta = row[metric_col]
            map_color = 'green' if delta < 0 else 'red'
        else:
            map_color = "steelblue"
        
        color  = map_color
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
    elif metric_col == "Perubahan AQI (%)":
        legend_html = """
        <div style="position: fixed; bottom: 30px; left: 30px; z-index:1000; background-color:white;padding: 10px; border-radius: 8px; font-size: 13px;">
        <b>Perubahan AQI 2013-2017</b><br>
        <i style="background:green;width:12px;height:12px;display:inline-block"></i> Kualitas Udara Membaik (% < 0)<br>
        <i style="background:red;width:12px;height:12px;display:inline-block"></i> Kualitas Udara Memburuk (% > 0)
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(legend_html))
    
    st_folium(m, width=900, height=520)


    # Rata-rata per stasiun
    st.subheader(f"Rata-rata {metric_col} per Stasiun")
    st.dataframe(
        df_map[["station", metric_col]]
        .rename(columns={metric_col: f"Avg {metric_col}"})
        .sort_values(f"Avg {metric_col}", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
    )


    # Peringkat stasiun
    st.subheader(f"Peringkat Stasiun berdasarkan {metric_col}")

    df_delta = df_delta.sort_values(by=metric_col, ascending=True).reset_index()
    values = df_delta[metric_col]

    fig, ax = plt.subplots(figsize=(10, 6))

    threshold = values.mean()

    colors_bar = [
        "#5774B7" if v >= threshold else "#D3D3D3"
        for v in values
    ]

    colors_percen_aqi = values.apply(lambda x: "green" if x < 0 else "red")

    bars = ax.barh(
        df_delta.station,
        values,
        color= colors_percen_aqi if metric_col == "Perubahan AQI (%)" else colors_bar,
        edgecolor = 'none'
    )

    ax.axvline(0, color="black", linewidth=1)

    for spine in ax.spines.values():
        spine.set_visible(False)

    for i, v in enumerate(values):
        ax.text(
            v,
            i,
            f"{v:.2f}",
            va="center",
            ha="left" if v > 0 else "right"
        )

    if metric_col != "Perubahan AQI (%)":
        legend_elements = [
            Patch(facecolor="#5774B7", label=f"{metric_col} > rata-rata"),
            Patch(facecolor="#D3D3D3", label=f"{metric_col} < rata-rata")
        ]

        ax.legend(
            handles=legend_elements,
            loc="upper left",
            bbox_to_anchor=(1.02, 1)
        )
    plt.tight_layout()
    st.pyplot(fig)

# === TAB 3 : ANALISIS KORELASI ====================================================
with tab_korelasi:
    # Pola musiman
    if granularity != "Yearly":
        st.subheader("Pola Musiman pada Variabel Polutan")
        
        polutan_select = st.multiselect("Pilih variabel polutan", POLLUTANTS, default=["PM2.5", "PM10"])
        if not polutan_select:
            st.warning("Pilih minimal satu variabel.")
            st.stop()

        df_filter["season"] = df_filter["month"].map(SEASON_MAPPING)
        df_season = (
            df_filter.groupby(['station','season'])[polutan_select]
            .mean()
            .reset_index()
        )
        station_order = df_season["station"].unique()

        fig, axes = plt.subplots(3, 2, figsize=(14, 20))
        axes = axes.flatten()

        for i, pol in enumerate(polutan_select):
            pivot = df_season.pivot(
                index='station', 
                columns='season', values=pol
            ).reindex(station_order)

            sns.heatmap(
                pivot,
                ax=axes[i],
                cmap='RdYlGn_r',
                annot=True,
                fmt='.1f',
                cbar=True,
                vmin=df_season[pol].min(),
                vmax=df_season[pol].max()
            )

            axes[i].set_title(pol)
            axes[i].set_xlabel('')
            axes[i].set_ylabel('')

        for j in range(len(polutan_select), len(axes)):
            fig.delaxes(axes[j])

        plt.tight_layout()
        st.pyplot(fig)


    # Korelasi
    st.subheader("Korelasi AQI vs Variabel Cuaca")
    
    all_param = POLLUTANTS + WEATHER_VARS
    param_select = st.multiselect("Pilih variabel", all_param, default=WEATHER_VARS)
    if not param_select:
        st.warning("Pilih minimal satu variabel.")
        st.stop()
    
    col_heatmap, col_scatter = st.columns([1, 2])

    with col_heatmap:
        st.markdown("#### Heatmap")
        corr_matrix = df_filter[['AQI'] + param_select].corr()
        correlation = corr_matrix.loc['AQI', param_select]
        correlation = correlation.to_frame()
        
        fig, ax = plt.subplots(figsize=(10, 3 * len(param_select)))

        sns.heatmap(
            correlation,
            ax=ax,
            annot=True,
            fmt=".2f",
            cmap='coolwarm',
            center=0,
            linewidths=0.5,
            annot_kws={"size": 34}
        )

        ax.set_title("Heatmap Korelasi Pearson")
        ax.set_ylabel("")
        ax.tick_params(axis='x', labelsize=34)
        ax.tick_params(axis='y', labelsize=34)

        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(labelsize=28)
        

        plt.tight_layout()
        st.pyplot(fig)


    with col_scatter:
        st.markdown("#### Scatterplot")
        
        fig, axes = plt.subplots(len(param_select), 2, figsize=(6, 2 * len(param_select)))
        axes = axes.flatten()

        for i, col in enumerate(param_select):
            sns.regplot(
                x=col,
                y='AQI',
                data=df_filter,
                ax=axes[i],
                scatter_kws={'alpha': 0.4},
                line_kws={'color': 'red'}
            )

            axes[i].set_title(f'AQI vs {col}')
            axes[i].set_xlabel("")
            axes[i].set_ylabel("AQI")

        for j in range(len(param_select), len(axes)):
            fig.delaxes(axes[j])

        plt.tight_layout()
        st.pyplot(fig)


st.caption('Copyright © Vini Emeralda 2026')