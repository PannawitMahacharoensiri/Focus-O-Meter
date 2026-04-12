from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st


st.set_page_config(page_title="Focus-O-Meter Analytics", page_icon="F", layout="wide")

if "dashboard_loaded" not in st.session_state:
    st.session_state["dashboard_loaded"] = False
if "weather_df" not in st.session_state:
    st.session_state["weather_df"] = pd.DataFrame()
if "attendance_df" not in st.session_state:
    st.session_state["attendance_df"] = pd.DataFrame()
if "tmd_df" not in st.session_state:
    st.session_state["tmd_df"] = pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_json_cached(base_url: str, endpoint: str, params_tuple: tuple[tuple[str, str], ...]):
    response = requests.get(f"{base_url}/{endpoint}/", params=dict(params_tuple), timeout=20)
    response.raise_for_status()
    return response.json()


def to_frame(records) -> pd.DataFrame:
    if not isinstance(records, list) or not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def normalize_params(params: dict) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in params.items()))


def parse_datetime_columns(frame: pd.DataFrame, candidates: list[str]) -> pd.DataFrame:
    if frame.empty:
        return frame
    updated = frame.copy()
    for column in candidates:
        if column in updated.columns:
            updated[column] = pd.to_datetime(updated[column], errors="coerce")
    return updated


def downsample_frame(frame: pd.DataFrame, max_points: int, sort_col: str | None = None) -> pd.DataFrame:
    if frame.empty or len(frame) <= max_points:
        return frame

    source = frame
    if sort_col and sort_col in source.columns:
        source = source.sort_values(sort_col)

    step = max(1, len(source) // max_points)
    return source.iloc[::step]


def map_direction_to_delta(value) -> int:
    if pd.isna(value):
        return 0

    normalized = str(value).strip().lower()
    if normalized in {"in", "เข้า", "enter", "entry"}:
        return 1
    if normalized in {"out", "ออก", "exit"}:
        return -1
    return 0


def normalize_classroom_value(value) -> str:
    if pd.isna(value):
        return "unknown"
    return str(value).strip().lower()


def extract_classroom_options(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "classroom" not in frame.columns:
        return []
    series = frame["classroom"].fillna("Unknown").astype(str).str.strip()
    series = series.replace("", "Unknown")
    return sorted(series.unique().tolist())


def apply_classroom_filter(frame: pd.DataFrame, selected_classes: list[str]) -> pd.DataFrame:
    if frame.empty or "classroom" not in frame.columns:
        return frame
    if not selected_classes:
        return frame.iloc[0:0]

    normalized_selected = {normalize_classroom_value(item) for item in selected_classes}
    classroom_series = frame["classroom"].fillna("Unknown").astype(str).str.strip()
    normalized_series = classroom_series.map(normalize_classroom_value)
    return frame[normalized_series.isin(normalized_selected)]


def build_csv_bytes(frame: pd.DataFrame) -> bytes:
    if frame.empty:
        return b""
    return frame.to_csv(index=False).encode("utf-8")


def preset_to_range(preset: str) -> tuple[datetime, datetime]:
    now = datetime.now()
    if preset == "Today":
        start = datetime(now.year, now.month, now.day, 0, 0, 0)
        end = datetime(now.year, now.month, now.day, 23, 59, 59)
        return start, end
    if preset == "Last 7 Days":
        end = now
        start = now - timedelta(days=7)
        return start, end
    if preset == "This Month":
        start = datetime(now.year, now.month, 1, 0, 0, 0)
        end = now
        return start, end

    default_start = datetime(now.year, 1, 1, 0, 0, 0)
    default_end = datetime(now.year, 12, 31, 23, 59, 59)
    return default_start, default_end


def render_weather_dashboard(
    frame: pd.DataFrame,
    selected_classes: list[str],
    max_plot_points: int,
    show_raw_tables: bool,
    max_table_rows: int,
) -> pd.DataFrame:
    st.subheader("In-class Weather")
    if frame.empty:
        st.info("No weather data returned.")
        return pd.DataFrame()

    filtered = apply_classroom_filter(frame, selected_classes)
    if filtered.empty:
        st.warning("No weather rows after applying classroom filter.")
        return pd.DataFrame()

    filtered = parse_datetime_columns(filtered, ["measuretime", "timestamp"])
    rows_col, class_col, temp_col = st.columns(3)
    rows_col.metric("Rows", len(filtered))
    class_count = filtered["classroom"].fillna("Unknown").nunique() if "classroom" in filtered.columns else 0
    class_col.metric("Classrooms", class_count)
    temp_col.metric("Avg Temp (C)", f"{filtered['temp_c'].mean():.2f}" if "temp_c" in filtered.columns else "N/A")

    if "measuretime" in filtered.columns and "temp_c" in filtered.columns:
        line_source = downsample_frame(filtered, max_plot_points, "measuretime").set_index("measuretime")
        st.markdown("Temperature over time")
        st.line_chart(line_source[["temp_c"]])

    metric_columns = [col for col in ["temp_c", "humid_p", "light_l", "sound_adc"] if col in filtered.columns]
    if metric_columns and "measuretime" in filtered.columns:
        st.markdown("Environmental trends")
        trend_source = downsample_frame(filtered, max_plot_points, "measuretime").set_index("measuretime")
        st.line_chart(trend_source[metric_columns])

    if "classroom" in filtered.columns and "sound_adc" in filtered.columns:
        st.markdown("Average sound by class")
        noise_group = (
            filtered.assign(classroom=filtered["classroom"].fillna("Unknown"))
            .groupby("classroom", as_index=False)["sound_adc"]
            .mean()
            .set_index("classroom")
        )
        st.bar_chart(noise_group)

    st.download_button(
        label="Download filtered weather CSV",
        data=build_csv_bytes(filtered),
        file_name="weather_filtered.csv",
        mime="text/csv",
        key="download_weather_csv",
    )
    if show_raw_tables:
        st.dataframe(filtered.head(max_table_rows), use_container_width=True)
    else:
        st.caption("Raw weather table hidden for performance. Enable in sidebar to view rows.")
    return filtered


def render_attendance_dashboard(
    frame: pd.DataFrame,
    selected_classes: list[str],
    max_plot_points: int,
    show_raw_tables: bool,
    max_table_rows: int,
) -> pd.DataFrame:
    st.subheader("Attendance")
    if frame.empty:
        st.info("No attendance data returned.")
        return pd.DataFrame()

    filtered = apply_classroom_filter(frame, selected_classes)
    if filtered.empty:
        st.warning("No attendance rows after applying classroom filter.")
        available = extract_classroom_options(frame)
        if available:
            st.caption(f"Available attendance classes: {', '.join(available)}")
        else:
            st.caption("Attendance rows are missing classroom values.")
        return pd.DataFrame()

    filtered = parse_datetime_columns(filtered, ["timestamp"])
    rows_col, class_col, direction_col = st.columns(3)
    rows_col.metric("Rows", len(filtered))
    class_count = filtered["classroom"].fillna("Unknown").nunique() if "classroom" in filtered.columns else 0
    class_col.metric("Classrooms", class_count)
    if "direction" in filtered.columns:
        direction_col.metric("Directions", filtered["direction"].nunique(dropna=True))
    else:
        direction_col.metric("Directions", "N/A")

    if "direction" in filtered.columns:
        st.markdown("Entry vs exit distribution")
        direction_counts = filtered["direction"].fillna("Unknown").value_counts().rename_axis("direction").to_frame("count")
        st.bar_chart(direction_counts)

    if "timestamp" in filtered.columns:
        st.markdown("Attendance events over time")
        events = (
            filtered.dropna(subset=["timestamp"])
            .set_index("timestamp")
            .sort_index()
            .resample("15min")
            .size()
            .to_frame("events")
        )
        if not events.empty:
            st.line_chart(downsample_frame(events.reset_index(), max_plot_points, "timestamp").set_index("timestamp"))

    if {"timestamp", "direction"}.issubset(filtered.columns):
        movement = filtered.copy()
        movement["delta"] = movement["direction"].map(map_direction_to_delta)
        movement = movement.dropna(subset=["timestamp"]).sort_values("timestamp")

        if not movement.empty:
            st.markdown("Net occupancy over time (IN = +1, OUT = -1)")
            movement["occupancy"] = movement["delta"].cumsum()
            occupancy_chart = downsample_frame(movement[["timestamp", "occupancy"]], max_plot_points, "timestamp").set_index("timestamp")
            st.line_chart(occupancy_chart)

            st.markdown("IN/OUT counts per 15-minute bucket")
            movement_bucket = movement.set_index("timestamp")
            in_out_bucket = pd.DataFrame(
                {
                    "in_count": (movement_bucket["delta"] == 1).resample("15min").sum(),
                    "out_count": (movement_bucket["delta"] == -1).resample("15min").sum(),
                }
            ).fillna(0)
            if not in_out_bucket.empty:
                in_out_bucket = downsample_frame(in_out_bucket.reset_index(), max_plot_points, "timestamp").set_index("timestamp")
                st.line_chart(in_out_bucket)

    if "classroom" in filtered.columns:
        st.markdown("Attendance count by class")
        class_counts = filtered["classroom"].fillna("Unknown").value_counts().rename_axis("classroom").to_frame("count")
        st.bar_chart(class_counts)

    st.download_button(
        label="Download filtered attendance CSV",
        data=build_csv_bytes(filtered),
        file_name="attendance_filtered.csv",
        mime="text/csv",
        key="download_attendance_csv",
    )
    if show_raw_tables:
        st.dataframe(filtered.head(max_table_rows), use_container_width=True)
    else:
        st.caption("Raw attendance table hidden for performance. Enable in sidebar to view rows.")
    return filtered


def render_tmd_dashboard(frame: pd.DataFrame, max_plot_points: int, show_raw_tables: bool, max_table_rows: int) -> pd.DataFrame:
    st.subheader("TMD Weather")
    if frame.empty:
        st.info("No TMD weather data returned.")
        return pd.DataFrame()

    filtered = parse_datetime_columns(frame, ["create_time"])
    rows_col, temp_col, rain_col = st.columns(3)
    rows_col.metric("Rows", len(filtered))
    temp_col.metric("Avg Temp (C)", f"{filtered['temp_c'].mean():.2f}" if "temp_c" in filtered.columns else "N/A")
    rain_col.metric("Avg Rainfall (mm)", f"{filtered['rainfal_mm'].mean():.2f}" if "rainfal_mm" in filtered.columns else "N/A")

    if "create_time" in filtered.columns:
        metric_columns = [col for col in ["temp_c", "humid_p", "rainfal_mm"] if col in filtered.columns]
        if metric_columns:
            st.markdown("TMD trends over time")
            trend_source = downsample_frame(filtered, max_plot_points, "create_time").set_index("create_time")
            st.line_chart(trend_source[metric_columns])

    if {"lat", "lon"}.issubset(filtered.columns):
        st.markdown("Station location map")
        st.map(filtered[["lat", "lon"]].dropna())

    st.download_button(
        label="Download filtered TMD CSV",
        data=build_csv_bytes(filtered),
        file_name="tmd_filtered.csv",
        mime="text/csv",
        key="download_tmd_csv",
    )
    if show_raw_tables:
        st.dataframe(filtered.head(max_table_rows), use_container_width=True)
    else:
        st.caption("Raw TMD table hidden for performance. Enable in sidebar to view rows.")
    return filtered


def render_cross_dataset_correlation(
    weather: pd.DataFrame,
    attendance: pd.DataFrame,
    bucket_rule: str,
    max_plot_points: int,
    show_raw_tables: bool,
    max_table_rows: int,
):
    st.subheader("Cross-Dataset Correlation")
    if weather.empty or attendance.empty:
        st.info("Correlation requires both weather and attendance data.")
        return

    weather_parsed = parse_datetime_columns(weather, ["measuretime"])
    attendance_parsed = parse_datetime_columns(attendance, ["timestamp"])

    if "measuretime" not in weather_parsed.columns or "timestamp" not in attendance_parsed.columns:
        st.info("Missing datetime columns needed for time-bucket correlation.")
        return
    if "sound_adc" not in weather_parsed.columns:
        st.info("Weather data is missing sound_adc for correlation analysis.")
        return

    weather_bucket = (
        weather_parsed.dropna(subset=["measuretime", "sound_adc"])
        .set_index("measuretime")
        .sort_index()
        .resample(bucket_rule)["sound_adc"]
        .mean()
        .to_frame("avg_sound")
    )

    attendance_bucket = (
        attendance_parsed.dropna(subset=["timestamp"])
        .set_index("timestamp")
        .sort_index()
        .resample(bucket_rule)
        .size()
        .to_frame("attendance_events")
    )

    merged = weather_bucket.join(attendance_bucket, how="inner").dropna()
    if merged.empty:
        st.warning("No overlapping time buckets between weather and attendance.")
        return

    corr_value = merged["avg_sound"].corr(merged["attendance_events"])
    points_col, corr_col = st.columns(2)
    points_col.metric("Overlapping buckets", len(merged))
    corr_col.metric("Pearson corr (sound vs events)", f"{corr_value:.3f}" if pd.notna(corr_value) else "N/A")

    st.markdown("Time-bucket trends")
    merged_line = merged.sort_index()
    if len(merged_line) > max_plot_points:
        step = max(1, len(merged_line) // max_plot_points)
        merged_line = merged_line.iloc[::step]
    st.line_chart(merged_line)

    st.markdown("Sound vs attendance scatter")
    merged_scatter = downsample_frame(merged.reset_index(), max_plot_points)
    st.scatter_chart(merged_scatter, x="avg_sound", y="attendance_events")

    st.download_button(
        label="Download correlation dataset CSV",
        data=build_csv_bytes(merged.reset_index()),
        file_name="correlation_sound_attendance.csv",
        mime="text/csv",
        key="download_correlation_csv",
    )
    if show_raw_tables:
        st.dataframe(merged.head(max_table_rows), use_container_width=True)
    else:
        st.caption("Raw correlation table hidden for performance. Enable in sidebar to view rows.")


st.title("Focus-O-Meter Analytics Dashboard")
st.caption("Visual analysis of classroom weather, attendance, and external weather data")

with st.sidebar:
    st.header("Data source")
    backend_base_url = st.text_input(
        "Backend API base URL",
        value="http://127.0.0.1:8000/api",
        help="Example: http://127.0.0.1:8000/api",
    ).rstrip("/")

    st.header("Filters")
    limit = st.number_input("Rows per dataset", min_value=100, max_value=200000, value=5000, step=100)
    date_mode = st.checkbox("Apply date range filter", value=False)
    bucket_rule = st.selectbox("Correlation time bucket", options=["15min", "30min", "1H", "1D"], index=1)
    st.header("Performance")
    max_plot_points = st.slider("Max points per plot", min_value=200, max_value=5000, value=1200, step=100)
    show_raw_tables = st.checkbox("Show raw data tables", value=False)
    max_table_rows = st.number_input("Max rows shown in table", min_value=100, max_value=20000, value=2000, step=100)

    start_text = ""
    end_text = ""
    if date_mode:
        preset = st.selectbox("Quick date preset", options=["Today", "Last 7 Days", "This Month", "Custom"], index=1)
        if preset == "Custom":
            default_start = datetime(2026, 1, 1, 0, 0, 0)
            default_end = datetime(2026, 12, 31, 23, 59, 59)
            start_dt = st.datetime_input("Start", value=default_start)
            end_dt = st.datetime_input("End", value=default_end)
        else:
            start_dt, end_dt = preset_to_range(preset)
            st.caption(f"Using preset range: {start_dt:%Y-%m-%d %H:%M:%S} to {end_dt:%Y-%m-%d %H:%M:%S}")

        start_text = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        end_text = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    st.caption("Class filter is discovered from returned data and applied to every dataset that contains a classroom field.")
    fetch = st.button("Load dashboard", type="primary", use_container_width=True)

if fetch:
    try:
        if date_mode:
            ranged_payload = fetch_json_cached(
                backend_base_url,
                "data_in_daterange",
                normalize_params({"start": start_text, "end": end_text, "limit": int(limit)}),
            )
            st.session_state["weather_df"] = to_frame(ranged_payload.get("weather", []))
            st.session_state["attendance_df"] = to_frame(ranged_payload.get("attendance", []))
            st.session_state["tmd_df"] = to_frame(ranged_payload.get("tmd", []))
        else:
            st.session_state["weather_df"] = to_frame(fetch_json_cached(backend_base_url, "weather", normalize_params({"limit": int(limit)})))
            st.session_state["attendance_df"] = to_frame(fetch_json_cached(backend_base_url, "attendance", normalize_params({"limit": int(limit)})))
            st.session_state["tmd_df"] = to_frame(fetch_json_cached(backend_base_url, "tmd_data", normalize_params({"limit": int(limit)})))

        st.session_state["dashboard_loaded"] = True
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")
        if not st.session_state["dashboard_loaded"]:
            st.stop()
    except ValueError:
        st.error("At least one endpoint returned invalid JSON.")
        if not st.session_state["dashboard_loaded"]:
            st.stop()

if not st.session_state["dashboard_loaded"]:
    st.info("Set filters in the sidebar and click Load dashboard.")
    st.stop()

weather_df = st.session_state["weather_df"]
attendance_df = st.session_state["attendance_df"]
tmd_df = st.session_state["tmd_df"]

weather_class_options = set(extract_classroom_options(weather_df))
attendance_class_options = set(extract_classroom_options(attendance_df))
common_class_options = sorted(weather_class_options.intersection(attendance_class_options))
all_class_options = sorted(weather_class_options.union(attendance_class_options))

class_scope = st.radio(
    "Classroom filter scope",
    options=["Common weather+attendance", "All discovered"],
    horizontal=True,
)

class_options = common_class_options if class_scope == "Common weather+attendance" else all_class_options

selected_classes = []
if class_options:
    selected_classes = st.multiselect("Classroom filter", options=class_options, default=class_options)
else:
    st.info("No classroom column available in the current data load.")

with st.expander("Available classes per dataset"):
    weather_label = ", ".join(sorted(weather_class_options)) if weather_class_options else "None"
    attendance_label = ", ".join(sorted(attendance_class_options)) if attendance_class_options else "None"
    st.write(f"Weather classes: {weather_label}")
    st.write(f"Attendance classes: {attendance_label}")

if selected_classes:
    selected_set = set(selected_classes)
    missing_in_attendance = sorted(selected_set.difference(attendance_class_options))
    missing_in_weather = sorted(selected_set.difference(weather_class_options))
    if missing_in_attendance:
        st.warning(f"Selected classes not found in attendance: {', '.join(missing_in_attendance)}")
    if missing_in_weather:
        st.warning(f"Selected classes not found in weather: {', '.join(missing_in_weather)}")

summary_left, summary_mid, summary_right = st.columns(3)
summary_left.metric("Weather rows", len(apply_classroom_filter(weather_df, selected_classes)))
summary_mid.metric("Attendance rows", len(apply_classroom_filter(attendance_df, selected_classes)))
summary_right.metric("TMD rows", len(tmd_df))

tab_weather, tab_attendance, tab_tmd, tab_correlation = st.tabs(["Weather", "Attendance", "TMD", "Correlation"])

with tab_weather:
    weather_filtered = render_weather_dashboard(weather_df, selected_classes, max_plot_points, show_raw_tables, int(max_table_rows))

with tab_attendance:
    attendance_filtered = render_attendance_dashboard(attendance_df, selected_classes, max_plot_points, show_raw_tables, int(max_table_rows))

with tab_tmd:
    tmd_filtered = render_tmd_dashboard(tmd_df, max_plot_points, show_raw_tables, int(max_table_rows))

with tab_correlation:
    render_cross_dataset_correlation(
        weather_filtered,
        attendance_filtered,
        bucket_rule,
        max_plot_points,
        show_raw_tables,
        int(max_table_rows),
    )
    combined_frames = []
    if not weather_filtered.empty:
        combined_frames.append(weather_filtered.assign(dataset="weather"))
    if not attendance_filtered.empty:
        combined_frames.append(attendance_filtered.assign(dataset="attendance"))
    if not tmd_filtered.empty:
        combined_frames.append(tmd_filtered.assign(dataset="tmd"))
    if combined_frames:
        combined_df = pd.concat(combined_frames, ignore_index=True, sort=False)
        st.download_button(
            label="Download all filtered datasets CSV",
            data=build_csv_bytes(combined_df),
            file_name="all_filtered_datasets.csv",
            mime="text/csv",
            key="download_all_filtered_csv",
        )
