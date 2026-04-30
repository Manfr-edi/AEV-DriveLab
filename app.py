import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import folium
import time
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from streamlit_folium import st_folium
from urllib.parse import quote

from aev_drivelab.scenario.sumo_route_tools import (
    AUTOWARE_EGO_VTYPE,
    DEFAULT_CARLA_HOST,
    DEFAULT_CARLA_PORT,
    DEFAULT_MAP,
    DEFAULT_EGO_BATTERY_CAPACITY,
    DEFAULT_EGO_BLUEPRINT,
    DEFAULT_VEHICLE_TYPE,
    EGO_SUMO_VTYPE,
    ENERGY_EMISSION_CLASS,
    MMPEVEM_EMISSION_CLASS,
    active_carla_version,
    available_carla_versions,
    available_maps,
    available_carla_vehicle_types,
    available_vehicle_types,
    build_run_command,
    current_sumo_dir,
    ego_emission_class_value,
    ego_model_defaults,
    edge_label,
    edge_direction_options,
    generate_congestion_scenario,
    generate_random_trips_scenario,
    carla_server_status,
    is_carla_server_ready,
    load_carla_map,
    nearest_edge,
    opposite_edge_id,
    read_ego_vtype_config,
    read_autoware_ego_vtype_config,
    read_sumo_edges,
    set_active_carla_version,
    start_carla_server,
    start_synchronization,
    stop_carla_server,
    launch_autoware_carla_in_container,
    write_ego_vtype_config,
    write_autoware_ego_vtype_config,
)

API_URL = "http://localhost:5000"
AUTOWARE_ALLOWED_MAPS = ("Town01", "Town04", "Town05")
STEP_CARLA_LABEL = "1. Start CARLA"
STEP_ROUTES_LABEL = "2. Generate SUMO Routes"
STEP_MONITORING_LABEL = "5. Monitoring"
EGO_ROUTE_VIA = "Pass through congested edge"
EGO_ROUTE_FROM_CONGESTION = "Use congested edge as start"
EGO_ROUTE_TO_CONGESTION = "Use congested edge as destination"
BASE_EGO_COLORS = [
    "white",
    "black",
    "gray",
    "silver",
    "red",
    "green",
    "blue",
    "yellow",
    "orange",
    "cyan",
    "magenta",
]
EGO_NUMERIC_LIMITS = {
    "minGap": (0.0, 20.0, 0.1),
    "maxSpeed": (0.1, 100.0, 0.1),
    "accel": (0.01, 20.0, 0.1),
    "decel": (0.01, 20.0, 0.1),
    "sigma": (0.0, 1.0, 0.01),
    "mass": (1.0, 100000.0, 10.0),
    "actionStepLength": (0.01, 10.0, 0.1),
    "airDragCoefficient": (0.0, 2.0, 0.01),
    "constantPowerIntake": (0.0, 100000.0, 10.0),
    "frontSurfaceArea": (0.1, 20.0, 0.01),
    "rotatingMass": (0.0, 10000.0, 1.0),
    "maximumPower": (0.0, 1000000.0, 1000.0),
    "propulsionEfficiency": (0.0, 1.0, 0.01),
    "radialDragCoefficient": (0.0, 2.0, 0.01),
    "recuperationEfficiency": (0.0, 1.0, 0.01),
    "rollDragCoefficient": (0.0, 1.0, 0.001),
    "stoppingThreshold": (0.0, 10.0, 0.1),
    "vehicleMass": (1.0, 100000.0, 10.0),
    "wheelRadius": (0.01, 5.0, 0.001),
    "internalMomentOfInertia": (0.0, 10000.0, 0.1),
    "gearRatio": (0.01, 100.0, 0.01),
    "gearEfficiency": (0.0, 1.0, 0.01),
    "maximumTorque": (0.0, 10000.0, 1.0),
    "maximumRecuperationTorque": (0.0, 10000.0, 1.0),
    "maximumRecuperationPower": (0.0, 1000000.0, 1000.0),
    "internalBatteryResistance": (0.0001, 10.0, 0.0001),
    "nominalBatteryVoltage": (1.0, 2000.0, 1.0),
}

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")


def preserve_scroll_position(storage_key="dashboard_scroll_position"):
    components.html(
        f"""
        <script>
        (() => {{
            const storageKey = {storage_key!r};
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;
            const handlerKey = `__streamlit_scroll_keeper_${{storageKey}}`;

            function isScrollable(element) {{
                if (!element) {{
                    return false;
                }}

                const style = parentWindow.getComputedStyle(element);
                return /(auto|scroll)/.test(style.overflowY)
                    && element.scrollHeight > element.clientHeight;
            }}

            function findScroller() {{
                const selectors = [
                    '[data-testid="stAppViewContainer"]',
                    'section.main',
                    '.main',
                ];

                for (const selector of selectors) {{
                    for (const element of parentDocument.querySelectorAll(selector)) {{
                        if (isScrollable(element)) {{
                            return element;
                        }}
                    }}
                }}

                for (const element of parentDocument.querySelectorAll('body *')) {{
                    if (isScrollable(element)) {{
                        return element;
                    }}
                }}

                return parentDocument.scrollingElement || parentDocument.documentElement;
            }}

            function getScrollY(scroller) {{
                if (
                    scroller === parentDocument.scrollingElement
                    || scroller === parentDocument.documentElement
                    || scroller === parentDocument.body
                ) {{
                    return parentWindow.scrollY || scroller.scrollTop || 0;
                }}

                return scroller.scrollTop || 0;
            }}

            function setScrollY(scroller, y) {{
                if (
                    scroller === parentDocument.scrollingElement
                    || scroller === parentDocument.documentElement
                    || scroller === parentDocument.body
                ) {{
                    parentWindow.scrollTo(0, y);
                }}

                scroller.scrollTop = y;
            }}

            const previousHandler = parentWindow[handlerKey];
            if (previousHandler) {{
                previousHandler.scroller.removeEventListener(
                    'scroll',
                    previousHandler.onScroll
                );
                parentWindow.removeEventListener(
                    'beforeunload',
                    previousHandler.save
                );
                parentWindow.removeEventListener('pagehide', previousHandler.save);
            }}

            const scroller = findScroller();
            const savedY = Number(parentWindow.sessionStorage.getItem(storageKey) || 0);

            if (savedY > 0) {{
                let attempts = 0;
                const restore = () => {{
                    setScrollY(scroller, savedY);
                    attempts += 1;

                    if (attempts < 60 && Math.abs(getScrollY(scroller) - savedY) > 2) {{
                        parentWindow.requestAnimationFrame(restore);
                    }}
                }};

                parentWindow.requestAnimationFrame(restore);
            }}

            let ticking = false;
            const save = () => {{
                parentWindow.sessionStorage.setItem(
                    storageKey,
                    String(getScrollY(scroller))
                );
                ticking = false;
            }};
            const onScroll = () => {{
                if (!ticking) {{
                    parentWindow.requestAnimationFrame(save);
                    ticking = true;
                }}
            }};

            scroller.addEventListener('scroll', onScroll, {{ passive: true }});
            parentWindow.addEventListener('beforeunload', save);
            parentWindow.addEventListener('pagehide', save);
            parentWindow[handlerKey] = {{ scroller, onScroll, save }};
        }})();
        </script>
        """,
        height=0,
    )

st.title("🚗 AEV - DriveLab")

# =====================================================
# BACKEND CHECK
# =====================================================

def is_backend_alive():
    try:
        r = requests.get(f"{API_URL}/state", timeout=0.5)
        return r.status_code == 200
    except:
        return False


backend_alive = is_backend_alive()

if not backend_alive:
    st.warning(
        # "Backend non attivo. Puoi comunque generare lo scenario traffico "
        # "e avviare la co-simulazione dal tab dedicato."
    "Backend is not active. You can still generate the traffic scenario and start the co-simulation from the dedicated tab. "
    )
else:
    st.success("🟢 Backend connected")

# =====================================================
# SESSION STATE
# =====================================================

for key, default in {
    "start_edge": None,
    "end_edge": None,
    "battery_data": [],
    "monitoring_samples": [],
    "monitoring_summary": None,
    "monitoring_export_paths": None,
    "monitoring_session_token": None,
    "monitoring_saved_session_token": None,
    "monitoring": False,
    "map_ready": False,
    "refresh_rate": 1000,
    "last_monitoring_poll": 0.0,
    "latest_monitoring_state": None,
    "monitoring_events": [],
    "dashboard_events": [],
    "vehicle_terminal_event": None,
    "last_vehicle_state": None,
    "monitoring_started_at": None,
    "traffic_map_name": DEFAULT_MAP,
    "runtime_map_selection": DEFAULT_MAP,
    "traffic_target_edge": "",
    "traffic_destination_edge": "",
    "traffic_source_edge": "",
    "traffic_last_click": None,
    "traffic_clicked_direction": "",
    "traffic_generation_result": None,
    "traffic_process": None,
    "traffic_process_log": None,
    "carla_process": None,
    "carla_process_log": None,
    "carla_server_action_level": None,
    "carla_server_action_message": None,
    "traffic_carla_mode": None,
    "traffic_carla_mode_selection": None,
    "traffic_carla_timeout_seconds": 120,
    "traffic_carla_timeout_selection": None,
    "traffic_sumo_gui": True,
    "traffic_sumo_gui_selection": None,
    "traffic_waiting_for_autoware": False,
    "traffic_start_gate_file": None,
    "selected_carla_version": None,
    "applied_carla_version": None,
    "applied_runtime_map": None,
    "ego_clicked_direction": "",
    "ego_use_traffic_route": False,
    "ego_traffic_route_mode": EGO_ROUTE_VIA,
    "ego_active_start_edge": None,
    "ego_active_end_edge": None,
    "ego_active_via_edge": None,
    "ego_config_loaded": False,
    "ego_config_version": None,
    "ego_carla_blueprint": DEFAULT_EGO_BLUEPRINT,
    "ego_emission_model": ENERGY_EMISSION_CLASS,
    "ego_last_emission_model": ENERGY_EMISSION_CLASS,
    "ego_max_battery_capacity": DEFAULT_EGO_BATTERY_CAPACITY,
    "ego_initial_battery": min(5000.0, DEFAULT_EGO_BATTERY_CAPACITY),
    "ego_battery_failure_threshold": 0.0,
    "ego_active_battery_failure_threshold": 0.0,
    "autoware_ego_config_loaded": False,
    "autoware_ego_config_version": None,
    "autoware_ego_carla_blueprint": AUTOWARE_EGO_VTYPE,
    "autoware_ego_emission_model": ENERGY_EMISSION_CLASS,
    "autoware_ego_last_emission_model": ENERGY_EMISSION_CLASS,
    "autoware_ego_max_battery_capacity": DEFAULT_EGO_BATTERY_CAPACITY,
    "autoware_ego_initial_battery": min(5000.0, DEFAULT_EGO_BATTERY_CAPACITY),
    "autoware_battery_failure_threshold": 0.0,
    "autoware_active_battery_failure_threshold": 0.0,
    "autoware_start_edge": None,
    "autoware_goal_edge": None,
    "autoware_start_edge_selection": "",
    "autoware_goal_edge_selection": "",
    "autoware_pending_start_edge_selection": None,
    "autoware_pending_goal_edge_selection": None,
    "autoware_last_click": None,
    "autoware_clicked_direction": "",
    "autoware_planner_speed_limit_kmh": 50.0,
    "autoware_sync_delay_seconds": 10,
    "autoware_sync_delay_selection": None,
    "autoware_last_launch": None,
    "monitor_vehicle_selected_id": None,
    "monitor_vehicle_loaded_for": None,
    "live_vehicle_selected_id": None,
    "live_vehicle_config_loaded_for": None,
    "live_vehicle_config_version": None,
    "live_vehicle_carla_blueprint": DEFAULT_EGO_BLUEPRINT,
    "live_vehicle_emission_model": ENERGY_EMISSION_CLASS,
    "live_vehicle_last_emission_model": ENERGY_EMISSION_CLASS,
    "live_vehicle_max_battery_capacity": DEFAULT_EGO_BATTERY_CAPACITY,
    "live_vehicle_has_battery_device": True,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def apply_selected_carla_version():
    versions = available_carla_versions()
    if not versions:
        st.error("No supported CARLA installation found in the project root.")
        st.stop()

    if st.session_state.selected_carla_version not in versions:
        if "0.9.13" in versions:
            default_version = "0.9.13"
        else:
            default_version = active_carla_version()
            if default_version not in versions:
                default_version = versions[-1]
        st.session_state.selected_carla_version = default_version

    control_cols = st.columns([1.2, 2.9, 1.3])
    with control_cols[0]:
        selected_version = st.selectbox(
            "CARLA version",
            options=versions,
            key="selected_carla_version",
        )

    previous_version = st.session_state.applied_carla_version
    set_active_carla_version(selected_version)
    if previous_version not in (None, selected_version):
        st.session_state.traffic_generation_result = None
        st.session_state.ego_config_loaded = False
        st.session_state.ego_config_version = None
        st.session_state.autoware_ego_config_loaded = False
        st.session_state.autoware_ego_config_version = None
        st.session_state.autoware_active_battery_failure_threshold = 0.0
        st.session_state.live_vehicle_config_loaded_for = None
        st.session_state.live_vehicle_config_version = None
        st.session_state.autoware_last_launch = None
        gate_file = st.session_state.get("traffic_start_gate_file")
        if gate_file:
            try:
                Path(gate_file).unlink(missing_ok=True)
            except OSError:
                pass
        st.session_state.traffic_waiting_for_autoware = False
        st.session_state.traffic_start_gate_file = None

    st.session_state.applied_carla_version = selected_version
    server_status = carla_server_status(selected_version)

    with control_cols[1]:
        st.caption(
            "Generated SUMO files, Town loading, and co-simulation startup use the selected "
            f"CARLA installation for version {selected_version}."
        )
        if server_status["running"]:
            detected_version = server_status.get("detected_version")
            if detected_version:
                st.caption(
                    f"CARLA server active on `{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}` "
                    f"from version `{detected_version}`."
                )
            elif server_status.get("external"):
                st.caption(
                    f"CARLA server active on `{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}`, "
                    "but not mapped to a local supported installation."
                )
            else:
                st.caption(
                    f"CARLA process detected. Server readiness on "
                    f"`{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}`: "
                    f"`{'ready' if server_status['ready'] else 'starting'}`."
                )
        else:
            st.caption(
                f"CARLA server inactive on `{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}`."
            )

    with control_cols[2]:
        toggle_label = (
            "Kill CARLA"
            if server_status["running"]
            else f"Run CARLA {selected_version}"
        )
        if st.button(toggle_label, key="toggle_carla_server", use_container_width=True):
            try:
                if server_status["running"]:
                    stop_version = server_status.get("detected_version")
                    stopped = stop_carla_server(stop_version)
                    st.session_state.carla_process = None
                    if stopped.get("port_closed"):
                        if stop_version:
                            message = (
                                f"CARLA {stop_version} stopped "
                                f"({len(stopped.get('stopped_pids', []))} process(es))."
                            )
                        else:
                            message = "CARLA stopped."
                        level = "warning"
                    else:
                        message = (
                            "Local CARLA processes were terminated, but port 2000 is still open."
                        )
                        level = "error"
                else:
                    selected_map = st.session_state.traffic_map_name
                    launch = start_carla_server(selected_version, map_name=selected_map)
                    st.session_state.carla_process = launch["process"]
                    st.session_state.carla_process_log = launch["log_file"]
                    message = (
                        f"CARLA {launch['version']} started, PID {launch['process'].pid}, "
                        f"Town `{selected_map}` loaded."
                    )
                    level = "success"
                st.session_state.carla_server_action_message = message
                st.session_state.carla_server_action_level = level
                st.rerun()
            except Exception as exc:
                st.error(f"CARLA server action failed: {exc}")

    event_message = st.session_state.carla_server_action_message
    event_level = st.session_state.carla_server_action_level
    if event_message:
        if event_level == "success":
            st.success(event_message)
        elif event_level == "warning":
            st.warning(event_message)
        elif event_level == "error":
            st.error(event_message)
        else:
            st.info(event_message)
        st.session_state.carla_server_action_message = None
        st.session_state.carla_server_action_level = None

    return selected_version


apply_selected_carla_version()


def format_elapsed(seconds):
    if seconds is None:
        return "-"

    minutes, seconds = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{seconds:02d}"


def extract_state_time(state):
    if not state:
        return None

    for key in ("time", "sim_time", "simulation_time", "timestamp"):
        value = state.get(key)
        if value is not None:
            return value

    return None


def _coerce_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_filename_fragment(value):
    text = str(value or "monitoring").strip()
    normalized = [
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in text
    ]
    return "".join(normalized).strip("._") or "monitoring"


def monitoring_output_dir():
    base_dir = current_sumo_dir() or Path(__file__).resolve().parent
    output_dir = Path(base_dir) / "output" / "monitoring"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def append_monitoring_sample(state):
    if not state:
        return

    wall_timestamp = time.time()
    started_at = st.session_state.monitoring_started_at
    elapsed_seconds = (
        max(0.0, wall_timestamp - started_at)
        if started_at is not None
        else None
    )

    sample = {
        "vehicle_id": state.get("vehicle_id"),
        "edge": state.get("edge"),
        "wall_timestamp": wall_timestamp,
        "wall_time": datetime.fromtimestamp(wall_timestamp).isoformat(timespec="seconds"),
        "elapsed_seconds": elapsed_seconds,
        "sim_time": _coerce_float(extract_state_time(state)),
        "speed_mps": _coerce_float(state.get("speed")),
        "battery_wh": _coerce_float(state.get("battery")),
        "distance_travelled_m": _coerce_float(state.get("distance_travelled_m")),
        "distance_remaining_m": _coerce_float(state.get("distance_remaining_m")),
        "route_final_edge": state.get("route_final_edge"),
    }

    samples = st.session_state.monitoring_samples
    if samples and sample["sim_time"] is not None:
        last_sim_time = samples[-1].get("sim_time")
        if last_sim_time is not None and abs(last_sim_time - sample["sim_time"]) < 1e-9:
            samples[-1] = sample
            return

    samples.append(sample)


def build_monitoring_summary(reason=None):
    samples = st.session_state.monitoring_samples
    if not samples:
        return None

    dataframe = pd.DataFrame(samples)
    vehicle_id = (
        dataframe["vehicle_id"].dropna().iloc[-1]
        if "vehicle_id" in dataframe and not dataframe["vehicle_id"].dropna().empty
        else st.session_state.monitor_vehicle_selected_id
    )
    terminal_event = st.session_state.vehicle_terminal_event or {}
    terminal_kind = terminal_event.get("kind")

    speed_series = dataframe["speed_mps"].dropna() if "speed_mps" in dataframe else pd.Series(dtype=float)
    battery_series = dataframe["battery_wh"].dropna() if "battery_wh" in dataframe else pd.Series(dtype=float)
    travelled_series = (
        dataframe["distance_travelled_m"].dropna()
        if "distance_travelled_m" in dataframe
        else pd.Series(dtype=float)
    )
    remaining_series = (
        dataframe["distance_remaining_m"].dropna()
        if "distance_remaining_m" in dataframe
        else pd.Series(dtype=float)
    )

    distance_travelled_m = float(travelled_series.iloc[-1]) if not travelled_series.empty else None
    distance_remaining_m = float(remaining_series.iloc[-1]) if not remaining_series.empty else None
    battery_initial_wh = float(battery_series.iloc[0]) if not battery_series.empty else None
    battery_final_wh = float(battery_series.iloc[-1]) if not battery_series.empty else None
    battery_consumed_wh = (
        battery_initial_wh - battery_final_wh
        if battery_initial_wh is not None and battery_final_wh is not None
        else None
    )
    average_consumption_wh_per_km = (
        battery_consumed_wh / (distance_travelled_m / 1000.0)
        if battery_consumed_wh is not None
        and distance_travelled_m is not None
        and distance_travelled_m > 0.0
        else None
    )

    speed_min_kmh = float(speed_series.min() * 3.6) if not speed_series.empty else None
    speed_max_kmh = float(speed_series.max() * 3.6) if not speed_series.empty else None
    speed_avg_kmh = float(speed_series.mean() * 3.6) if not speed_series.empty else None

    arrived = (
        terminal_kind == "destination_reached"
        or (distance_remaining_m is not None and distance_remaining_m <= 1.0)
    )

    return {
        "vehicle_id": vehicle_id,
        "reason": reason or terminal_kind or "stopped",
        "sample_count": int(len(samples)),
        "wall_time_started": (
            datetime.fromtimestamp(st.session_state.monitoring_started_at).isoformat(timespec="seconds")
            if st.session_state.monitoring_started_at is not None
            else None
        ),
        "wall_time_finished": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": (
            float(dataframe["elapsed_seconds"].dropna().iloc[-1])
            if "elapsed_seconds" in dataframe and not dataframe["elapsed_seconds"].dropna().empty
            else None
        ),
        "sim_time_finished": (
            float(dataframe["sim_time"].dropna().iloc[-1])
            if "sim_time" in dataframe and not dataframe["sim_time"].dropna().empty
            else None
        ),
        "terminal_event": terminal_kind,
        "arrived": bool(arrived),
        "distance_travelled_m": distance_travelled_m,
        "distance_remaining_m": 0.0 if arrived else distance_remaining_m,
        "battery_initial_wh": battery_initial_wh,
        "battery_final_wh": battery_final_wh,
        "battery_consumed_wh": battery_consumed_wh,
        "average_consumption_wh_per_km": average_consumption_wh_per_km,
        "speed_min_kmh": speed_min_kmh,
        "speed_max_kmh": speed_max_kmh,
        "speed_avg_kmh": speed_avg_kmh,
    }


def persist_monitoring_session(reason=None):
    samples = st.session_state.monitoring_samples
    session_token = st.session_state.monitoring_session_token
    if not samples or session_token is None:
        return None
    if st.session_state.monitoring_saved_session_token == session_token:
        return st.session_state.monitoring_summary

    summary = build_monitoring_summary(reason=reason)
    if summary is None:
        return None

    dataframe = pd.DataFrame(samples)
    battery_initial_wh = summary.get("battery_initial_wh")
    if battery_initial_wh is not None and "battery_wh" in dataframe:
        dataframe["battery_consumed_wh"] = dataframe["battery_wh"].apply(
            lambda value: battery_initial_wh - value if pd.notna(value) else None
        )
    if "speed_mps" in dataframe:
        dataframe["speed_kmh"] = dataframe["speed_mps"].apply(
            lambda value: value * 3.6 if pd.notna(value) else None
        )

    output_dir = monitoring_output_dir()
    vehicle_fragment = _safe_filename_fragment(summary.get("vehicle_id"))
    csv_path = output_dir / f"{session_token}_{vehicle_fragment}_monitoring.csv"
    json_path = output_dir / f"{session_token}_{vehicle_fragment}_summary.json"

    dataframe.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    st.session_state.monitoring_summary = summary
    st.session_state.monitoring_export_paths = {
        "csv": str(csv_path),
        "json": str(json_path),
    }
    st.session_state.monitoring_saved_session_token = session_token
    return summary


def render_saved_monitoring_summary():
    summary = st.session_state.get("monitoring_summary")
    if not summary:
        return

    st.write("### Monitoring Summary")
    summary_cols = st.columns(4)
    summary_cols[0].metric(
        "Remaining distance",
        "0 m" if summary.get("arrived") else (
            "-"
            if summary.get("distance_remaining_m") is None
            else f"{summary['distance_remaining_m']:.1f} m"
        ),
    )
    summary_cols[1].metric(
        "Avg consumption",
        "-"
        if summary.get("average_consumption_wh_per_km") is None
        else f"{summary['average_consumption_wh_per_km']:.1f} Wh/km",
    )
    summary_cols[2].metric(
        "Battery used",
        "-"
        if summary.get("battery_consumed_wh") is None
        else f"{summary['battery_consumed_wh']:.1f} Wh",
    )
    summary_cols[3].metric(
        "Avg speed",
        "-"
        if summary.get("speed_avg_kmh") is None
        else f"{summary['speed_avg_kmh']:.1f} km/h",
    )

    speed_cols = st.columns(3)
    speed_cols[0].metric(
        "Min speed",
        "-"
        if summary.get("speed_min_kmh") is None
        else f"{summary['speed_min_kmh']:.1f} km/h",
    )
    speed_cols[1].metric(
        "Max speed",
        "-"
        if summary.get("speed_max_kmh") is None
        else f"{summary['speed_max_kmh']:.1f} km/h",
    )
    speed_cols[2].metric(
        "Distance travelled",
        "-"
        if summary.get("distance_travelled_m") is None
        else f"{summary['distance_travelled_m']:.1f} m",
    )

    export_paths = st.session_state.get("monitoring_export_paths") or {}
    if export_paths.get("csv"):
        st.caption(f"Saved CSV: `{export_paths['csv']}`")
    if export_paths.get("json"):
        st.caption(f"Saved JSON: `{export_paths['json']}`")


def vehicle_setup_step_label():
    if active_carla_version() == "0.9.13":
        return "4. Launch Autoware AV"
    return "3. Spawn SUMO Ego Vehicle"


def simulation_step_label():
    if active_carla_version() == "0.9.13":
        return "3. Configure Simulation"
    return "4. Run Simulation"


def runtime_map_options():
    allowed_maps = [map_name for map_name in available_maps() if map_name in AUTOWARE_ALLOWED_MAPS]
    return allowed_maps or available_maps()


def apply_selected_runtime_map():
    maps = runtime_map_options()
    if not maps:
        st.error("No SUMO/CARLA Town is available in the selected installation.")
        st.stop()

    if st.session_state.traffic_map_name not in maps:
        st.session_state.traffic_map_name = DEFAULT_MAP if DEFAULT_MAP in maps else maps[0]

    selected_map = st.session_state.traffic_map_name
    previous_map = st.session_state.applied_runtime_map
    if previous_map not in (None, selected_map):
        st.session_state.traffic_generation_result = None
        st.session_state.traffic_target_edge = ""
        st.session_state.traffic_destination_edge = ""
        st.session_state.traffic_source_edge = ""
        st.session_state.traffic_last_click = None
        st.session_state.traffic_clicked_direction = ""
        st.session_state.start_edge = None
        st.session_state.end_edge = None
        st.session_state.last_click = None
        st.session_state.ego_clicked_direction = ""
        st.session_state.autoware_start_edge = None
        st.session_state.autoware_goal_edge = None
        st.session_state.autoware_start_edge_selection = ""
        st.session_state.autoware_goal_edge_selection = ""
        st.session_state.autoware_pending_start_edge_selection = None
        st.session_state.autoware_pending_goal_edge_selection = None
        st.session_state.autoware_last_click = None
        st.session_state.autoware_clicked_direction = ""
        st.session_state.autoware_last_launch = None
        st.session_state.autoware_active_battery_failure_threshold = 0.0
        clear_waiting_synchronization_state(remove_gate_file=True)

    st.session_state.applied_runtime_map = selected_map
    return selected_map, maps


def ensure_simulation_launch_defaults():
    carla_server_ready = is_carla_server_ready()
    if st.session_state.traffic_carla_mode is None:
        st.session_state.traffic_carla_mode = "reuse" if carla_server_ready else "prepare"
    return carla_server_ready


def sync_launch_command_for_ui(sumocfg_file):
    return build_run_command(
        sumocfg_file,
        sumo_gui=bool(st.session_state.traffic_sumo_gui),
    )


def sync_launch_widget_defaults():
    if st.session_state.traffic_carla_mode_selection not in {"reuse", "prepare"}:
        st.session_state.traffic_carla_mode_selection = st.session_state.traffic_carla_mode
    if not isinstance(st.session_state.traffic_sumo_gui_selection, bool):
        st.session_state.traffic_sumo_gui_selection = bool(st.session_state.traffic_sumo_gui)
    if not isinstance(st.session_state.traffic_carla_timeout_selection, int):
        st.session_state.traffic_carla_timeout_selection = int(
            st.session_state.traffic_carla_timeout_seconds
        )
    if not isinstance(st.session_state.autoware_sync_delay_selection, int):
        st.session_state.autoware_sync_delay_selection = int(
            st.session_state.autoware_sync_delay_seconds
        )


def effective_autoware_startup_wait_seconds(sumo_gui=None):
    configured_wait = int(st.session_state.autoware_sync_delay_seconds)
    if sumo_gui is None:
        sumo_gui = bool(st.session_state.traffic_sumo_gui)
    return 0 if sumo_gui else configured_wait


def autoware_launch_sync_state():
    launch = st.session_state.autoware_last_launch
    if not launch:
        return None

    started_at = launch.get("started_at")
    if started_at is None:
        return None

    wait_seconds = int(launch.get("startup_wait_seconds", 0))
    ready_at = float(started_at) + max(wait_seconds, 0)
    remaining_seconds = max(0.0, ready_at - time.time())
    return {
        "map_name": launch.get("map_name"),
        "container_name": launch.get("container_name"),
        "started_at": float(started_at),
        "startup_wait_seconds": wait_seconds,
        "ready_at": ready_at,
        "remaining_seconds": remaining_seconds,
        "is_ready": remaining_seconds <= 1e-6,
    }


def waiting_for_autoware_sync():
    sync_process = st.session_state.traffic_process
    sync_running = sync_process is not None and sync_process.poll() is None
    if st.session_state.traffic_waiting_for_autoware and not sync_running:
        clear_waiting_synchronization_state(remove_gate_file=True)
        return False
    return bool(st.session_state.traffic_waiting_for_autoware and sync_running)


def clear_waiting_synchronization_state(remove_gate_file=False):
    gate_file = st.session_state.traffic_start_gate_file
    if remove_gate_file and gate_file:
        try:
            Path(gate_file).unlink(missing_ok=True)
        except OSError:
            pass
    st.session_state.traffic_waiting_for_autoware = False
    st.session_state.traffic_start_gate_file = None


def release_waiting_synchronization_gate():
    gate_file = st.session_state.traffic_start_gate_file
    if not gate_file:
        raise RuntimeError("No SUMO start gate is armed for the current session.")

    gate_path = Path(gate_file)
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text("start\n", encoding="utf-8")
    clear_waiting_synchronization_state(remove_gate_file=False)


def start_dashboard_synchronization_launch(
    result,
    carla_mode,
    carla_timeout,
    sumo_gui,
    wait_for_autoware=False,
):
    carla_server_ready = is_carla_server_ready()
    if carla_mode == "reuse" and not carla_server_ready:
        raise RuntimeError(
            f"CARLA is not reachable on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}. "
            "Start CARLA first or switch to 'Start CARLA and load the Town'."
        )

    launch = start_synchronization(
        result.sumocfg_file,
        map_name=result.map_name,
        ensure_carla=(carla_mode == "prepare"),
        carla_process=st.session_state.carla_process,
        carla_timeout=int(carla_timeout),
        sumo_gui=bool(sumo_gui),
        wait_for_start=bool(wait_for_autoware),
    )

    st.session_state.traffic_process = launch.sync_process
    st.session_state.traffic_process_log = launch.sync_log_file
    st.session_state.carla_process = launch.carla_process
    st.session_state.carla_process_log = launch.carla_log_file
    st.session_state.traffic_waiting_for_autoware = launch.start_gate_file is not None
    st.session_state.traffic_start_gate_file = (
        str(launch.start_gate_file) if launch.start_gate_file is not None else None
    )
    return launch


def synchronization_success_message(launch, result, carla_mode, sumo_gui):
    if launch.start_gate_file is not None:
        message = (
            f"SUMO/CARLA bridge started, PID {launch.sync_process.pid}, "
            "and is waiting for Autoware before simulation time advances."
        )
    else:
        message = f"Co-simulation started, PID {launch.sync_process.pid}."
    if carla_mode == "reuse":
        message += (
            f" Using CARLA already running on "
            f"{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}."
        )
    if launch.map_loaded:
        message += f" Town {result.map_name} loaded."
    if carla_mode != "reuse" and launch.carla_started:
        message += " CARLA started."
    message += " SUMO GUI enabled." if sumo_gui else " SUMO running headless."
    return message


def render_carla_step():
    selected_version = active_carla_version()
    status = carla_server_status(selected_version)
    sync_process = st.session_state.traffic_process
    sync_running = sync_process is not None and sync_process.poll() is None
    selected_map, maps = apply_selected_runtime_map()
    if st.session_state.runtime_map_selection not in maps:
        st.session_state.runtime_map_selection = selected_map

    st.subheader("🚘 Start CARLA")
    st.caption(
        "Select the Town here. All following steps use this Town and no longer expose a separate map selector."
    )

    town_cols = st.columns([2, 3])
    with town_cols[0]:
        selected_map_choice = st.selectbox(
            "Selected Town",
            options=maps,
            index=edge_select_index(maps, st.session_state.runtime_map_selection),
            key="runtime_map_selection",
            disabled=sync_running,
        )
    with town_cols[1]:
        if sync_running:
            st.caption(
                "The Town selector is locked while the co-simulation is running."
            )
        else:
            st.caption(
                "This Town will be used by SUMO route generation, Autoware launch, and the co-simulation startup."
            )

    if selected_map_choice != st.session_state.traffic_map_name:
        st.session_state.traffic_map_name = selected_map_choice
    selected_map, _ = apply_selected_runtime_map()

    if status["running"]:
        detected_version = status.get("detected_version")
        if detected_version:
            st.success(
                f"CARLA server is active on `{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}` "
                f"for version `{detected_version}`."
            )
        else:
            st.success(
                f"CARLA server is active on `{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}`."
            )
    else:
        st.warning(
            f"CARLA is not running on `{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}`."
        )

    if status["running"] and status.get("detected_version") not in (None, selected_version):
        st.warning(
            f"The selected version is `{selected_version}`, but the running CARLA server "
            f"was detected as `{status['detected_version']}`."
        )

    info_cols = st.columns(3)
    info_cols[0].metric("Selected CARLA", selected_version)
    info_cols[1].metric("Selected Town", selected_map)
    info_cols[2].metric("Status", "Running" if status["running"] else "Stopped")

    if status["running"]:
        load_cols = st.columns([1, 3])
        with load_cols[0]:
            if st.button("Load selected Town", use_container_width=True):
                try:
                    with st.spinner(f"Loading `{selected_map}` in CARLA..."):
                        load_carla_map(selected_map)
                    st.success(f"Town `{selected_map}` loaded in CARLA.")
                except Exception as exc:
                    st.error(f"Town load failed: {exc}")
        with load_cols[1]:
            st.caption(
                "Use this if CARLA is already running and you want to force the selected Town before the next steps."
            )

    if st.session_state.carla_process_log:
        st.caption(f"CARLA Log: {st.session_state.carla_process_log}")


def reset_monitoring_trip_state():
    st.session_state.battery_data = []
    st.session_state.monitoring_samples = []
    st.session_state.monitoring_summary = None
    st.session_state.monitoring_export_paths = None
    st.session_state.monitoring_session_token = None
    st.session_state.monitoring_saved_session_token = None
    st.session_state.dashboard_events = []
    st.session_state.vehicle_terminal_event = None
    st.session_state.latest_monitoring_state = None
    st.session_state.last_vehicle_state = None
    st.session_state.monitoring_events = []
    st.session_state.last_monitoring_poll = 0.0
    st.session_state.monitoring_started_at = None


def record_dashboard_event(kind, state):
    if st.session_state.vehicle_terminal_event is not None:
        return

    vehicle_id = state.get("vehicle_id", "-") if state else "-"
    edge = state.get("edge", "-") if state else "-"
    battery = state.get("battery") if state else None
    wall_time = datetime.now().strftime("%H:%M:%S")
    elapsed = None

    if st.session_state.monitoring_started_at is not None:
        elapsed = time.time() - st.session_state.monitoring_started_at

    event = {
        "kind": kind,
        "vehicle_id": vehicle_id,
        "edge": edge,
        "battery": battery,
        "wall_time": wall_time,
        "elapsed": format_elapsed(elapsed),
        "sim_time": extract_state_time(state),
    }

    if kind == "battery_depleted":
        default_threshold = (
            st.session_state.ego_active_battery_failure_threshold
            if vehicle_id == "ego_vehicle"
            else st.session_state.autoware_active_battery_failure_threshold
        )
        threshold = state.get(
            "battery_failure_threshold",
            default_threshold,
        ) if state else default_threshold
        event["message"] = (
            f"[{vehicle_id}] Battery below critical threshold "
            f"({threshold} Wh): failure at {wall_time}, "
            f"t={event['elapsed']}, edge={edge}"
        )
    elif kind == "destination_reached":
        event["message"] = (
            f"[{vehicle_id}] Destination reached "
            f"at {wall_time}, t={event['elapsed']}, edge={edge}"
        )
    else:
        event["message"] = f"[{vehicle_id}] Vehicle event at {wall_time}, edge={edge}"

    if event["sim_time"] is not None:
        event["message"] += f", t_sim={event['sim_time']}"

    st.session_state.vehicle_terminal_event = event
    st.session_state.dashboard_events.append(event)


def update_vehicle_events(state):
    if not state:
        return

    st.session_state.last_vehicle_state = state

    vehicle_id = state.get("vehicle_id") or st.session_state.monitor_vehicle_selected_id
    edge = state.get("edge")
    raw_battery = state.get("battery")

    try:
        battery = float(raw_battery) if raw_battery is not None else None
    except (TypeError, ValueError):
        battery = None

    default_threshold = (
        st.session_state.ego_active_battery_failure_threshold
        if vehicle_id == "ego_vehicle"
        else st.session_state.autoware_active_battery_failure_threshold
    )
    failure_threshold = float(
        state.get(
            "battery_failure_threshold",
            default_threshold,
        )
        or 0
    )
    if battery is not None and battery <= failure_threshold:
        record_dashboard_event("battery_depleted", state)
        st.session_state.monitoring = False
        return

    if vehicle_id != "ego_vehicle":
        return

    remaining_distance_m = _coerce_float(state.get("distance_remaining_m"))
    if remaining_distance_m is not None and remaining_distance_m <= 1.0:
        record_dashboard_event("destination_reached", state)
        st.session_state.monitoring = False
        return

    destination_edge = (
        st.session_state.autoware_goal_edge
        if st.session_state.autoware_last_launch and st.session_state.autoware_goal_edge
        else (st.session_state.ego_active_end_edge or st.session_state.end_edge)
    )
    if destination_edge and edge == destination_edge:
        record_dashboard_event("destination_reached", state)


def render_event(event):
    if isinstance(event, dict):
        kind = event.get("kind")
        message = event.get("message", str(event))

        if kind == "battery_depleted":
            st.error(message)
        elif kind == "destination_reached":
            st.success(message)
        else:
            st.write(message)
    else:
        st.write(event)


@st.fragment(run_every=0.5)
def render_monitoring():
    st.subheader("📊 Monitoring")

    if not backend_alive:
        st.warning("Start the co-simulation from the simulation step before monitoring.")
        render_saved_monitoring_summary()
        return

    try:
        live_vehicles = get_live_sumo_vehicles()
    except Exception as exc:
        st.error(f"Could not load vehicles for monitoring: {exc}")
        render_saved_monitoring_summary()
        return

    monitoring_candidates = [
        vehicle
        for vehicle in live_vehicles
        if vehicle.get("id") == "ego_vehicle" or is_carla_spawned_vehicle(vehicle)
    ]
    if not monitoring_candidates:
        if st.session_state.monitoring:
            st.session_state.monitoring = False
            persist_monitoring_session("vehicle_unavailable")
        st.info("No ego or CARLA-spawned SUMO vehicle is currently active.")
        render_saved_monitoring_summary()
        return

    candidate_ids = [vehicle["id"] for vehicle in monitoring_candidates]
    candidate_labels = {
        vehicle["id"]: vehicle_display_label(vehicle)
        for vehicle in monitoring_candidates
    }
    preferred_vehicle_id = preferred_monitoring_vehicle_id(monitoring_candidates)
    current_vehicle_id = st.session_state.monitor_vehicle_selected_id

    if current_vehicle_id not in candidate_ids:
        current_vehicle_id = preferred_vehicle_id
    elif (
        current_vehicle_id == "ego_vehicle"
        and preferred_vehicle_id
        and preferred_vehicle_id != current_vehicle_id
    ):
        current_vehicle_id = preferred_vehicle_id

    st.session_state.monitor_vehicle_selected_id = current_vehicle_id
    selected_vehicle_id = current_vehicle_id
    st.caption(f"Monitoring target: {candidate_labels[selected_vehicle_id]}")

    if st.session_state.monitor_vehicle_loaded_for != selected_vehicle_id:
        persist_monitoring_session("target_changed")
        reset_monitoring_trip_state()
        st.session_state.monitor_vehicle_loaded_for = selected_vehicle_id

    refresh_rate = st.slider(
        "Refresh rate (ms)",
        min_value=500,
        max_value=5000,
        step=500,
        key="refresh_rate",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Start Monitoring", disabled=st.session_state.monitoring):
            reset_monitoring_trip_state()
            st.session_state.monitoring = True
            st.session_state.monitoring_session_token = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.last_monitoring_poll = 0.0
            st.session_state.monitoring_started_at = time.time()

    with col2:
        if st.button("Stop Monitoring", disabled=not st.session_state.monitoring):
            st.session_state.monitoring = False
            persist_monitoring_session("manual_stop")

    chart_placeholder = st.empty()
    consumption_chart_placeholder = st.empty()
    metrics_placeholder = st.empty()
    battery_event_placeholder = st.empty()
    event_placeholder = st.empty()

    if st.session_state.monitoring:
        now = time.monotonic()
        elapsed_ms = (now - st.session_state.last_monitoring_poll) * 1000

        if elapsed_ms >= refresh_rate:
            try:
                response = requests.get(
                    f"{API_URL}/state",
                    params={"veh_id": selected_vehicle_id},
                    timeout=1,
                )
                res = response.json() if response.status_code == 200 else None
            except Exception:
                res = None

            if res:
                st.session_state.latest_monitoring_state = res
                raw_battery = res.get("battery")
                try:
                    battery_val = float(raw_battery) if raw_battery is not None else None
                except (TypeError, ValueError):
                    battery_val = None

                if battery_val is not None:
                    st.session_state.battery_data.append(battery_val)
                append_monitoring_sample(res)
                update_vehicle_events(res)

            try:
                st.session_state.monitoring_events = requests.get(
                    f"{API_URL}/events",
                    timeout=1,
                ).json()
            except Exception:
                pass

            st.session_state.last_monitoring_poll = now

    if st.session_state.monitoring_session_token and not st.session_state.monitoring:
        terminal_event = st.session_state.vehicle_terminal_event or {}
        persist_monitoring_session(terminal_event.get("kind") or "stopped")

    if st.session_state.battery_data:
        df = pd.DataFrame(st.session_state.battery_data, columns=["battery"])
        chart_placeholder.line_chart(df)
    if st.session_state.monitoring_samples:
        monitoring_df = pd.DataFrame(st.session_state.monitoring_samples)
        if "battery_wh" in monitoring_df and not monitoring_df["battery_wh"].dropna().empty:
            battery_initial = monitoring_df["battery_wh"].dropna().iloc[0]
            monitoring_df["battery_consumed_wh"] = monitoring_df["battery_wh"].apply(
                lambda value: battery_initial - value if pd.notna(value) else None
            )
            consumption_chart_placeholder.line_chart(
                monitoring_df[["battery_consumed_wh"]]
            )

    res = st.session_state.latest_monitoring_state
    if res:
        raw_battery = res.get("battery")
        try:
            battery_val = float(raw_battery) if raw_battery is not None else None
        except (TypeError, ValueError):
            battery_val = None
        speed = _coerce_float(res.get("speed"))
        remaining_distance_m = _coerce_float(res.get("distance_remaining_m"))
        edge = res.get("edge", "-")
        vehicle_id = res.get("vehicle_id", selected_vehicle_id)

        with metrics_placeholder.container():
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🚘 Vehicle", vehicle_id)
            c2.metric("🔋 Battery", "-" if battery_val is None else battery_val)
            c3.metric(
                "🚗 Speed",
                "-" if speed is None else f"{speed * 3.6:.1f} km/h",
            )
            c4.metric("🛣️ Edge", edge)
            c5.metric(
                "🎯 Remaining",
                "-"
                if remaining_distance_m is None
                else f"{remaining_distance_m:.1f} m",
            )

        if battery_val is not None and battery_val <= 0:
            battery_event_placeholder.error("⚠️ Battery depleted!")
    elif st.session_state.monitoring:
        metrics_placeholder.info("Waiting for vehicle state...")

    with event_placeholder.container():
        st.write("### 🚨 Events")
        events = st.session_state.dashboard_events + st.session_state.monitoring_events

        if events:
            for e in events[-8:]:
                render_event(e)
        else:
            st.write("No events yet.")

    render_saved_monitoring_summary()


def get_network():
    if "network" not in st.session_state:
        res = requests.get(f"{API_URL}/network", timeout=2).json()
        st.session_state.network = res["edges"]

    return st.session_state.network


def to_map_coords(x, y):
    return [y, x]


@st.cache_data(show_spinner=False)
def get_offline_edges(map_name):
    return read_sumo_edges(map_name)


@st.cache_data(show_spinner=False)
def get_sumo_vtypes():
    return available_vehicle_types()


def edge_select_index(options, current_value):
    try:
        return options.index(current_value)
    except ValueError:
        return 0


def pick_auto_edge(edges, excluded=None, preferred=()):
    excluded = {edge_id for edge_id in (excluded or []) if edge_id}
    edge_by_id = {edge.edge_id: edge for edge in edges}

    for edge_id in preferred:
        if edge_id and edge_id in edge_by_id and edge_id not in excluded:
            return edge_id

    candidates = [edge for edge in edges if edge.edge_id not in excluded]
    if not candidates:
        return None

    return max(candidates, key=lambda edge: (edge.length, edge.lane_count, edge.edge_id)).edge_id


def generated_route_hints(route_file, target_edge):
    if not route_file or not target_edge:
        return None, None

    try:
        root = ET.parse(route_file).getroot()
    except (ET.ParseError, OSError):
        return None, None

    fallback = (None, None)

    for route in root.findall(".//route"):
        route_edges = (route.get("edges") or "").split()
        if target_edge not in route_edges:
            continue

        candidate = (route_edges[0], route_edges[-1])
        if fallback == (None, None):
            fallback = candidate

        target_index = route_edges.index(target_edge)
        if 0 < target_index < len(route_edges) - 1:
            return candidate

    return fallback


def apply_vtype_config_to_state(prefix, config):
    attribute_defaults, parameter_defaults = ego_model_defaults(config["emission_model"])
    merged_attributes = dict(attribute_defaults)
    merged_attributes.update(config.get("attributes") or {})
    merged_parameters = dict(parameter_defaults)
    merged_parameters.update(config.get("parameters") or {})

    st.session_state[f"{prefix}_sumo_vtype"] = config.get("sumo_vtype", "")
    st.session_state[f"{prefix}_carla_blueprint"] = config["carla_blueprint"]
    st.session_state[f"{prefix}_emission_model"] = config["emission_model"]
    st.session_state[f"{prefix}_last_emission_model"] = config["emission_model"]
    st.session_state[f"{prefix}_max_battery_capacity"] = config["battery_capacity"]
    if "battery_charge_level" in config:
        st.session_state[f"{prefix}_initial_battery"] = config["battery_charge_level"]
    st.session_state[f"{prefix}_has_battery_device"] = bool(
        config.get("has_battery_device", True)
    )

    for key, value in merged_attributes.items():
        st.session_state[f"{prefix}_attr_{key}"] = value
    for key, value in merged_parameters.items():
        st.session_state[f"{prefix}_param_{key}"] = value


def initialize_ego_config_state():
    current_version = active_carla_version()
    if (
        st.session_state.ego_config_loaded
        and st.session_state.ego_config_version == current_version
    ):
        return

    config = read_ego_vtype_config()
    apply_vtype_config_to_state("ego", config)
    st.session_state.ego_initial_battery = min(
        st.session_state.ego_initial_battery,
        config["battery_capacity"],
    )
    st.session_state.ego_config_loaded = True
    st.session_state.ego_config_version = current_version


def initialize_autoware_ego_config_state():
    current_version = active_carla_version()
    if (
        st.session_state.autoware_ego_config_loaded
        and st.session_state.autoware_ego_config_version == current_version
    ):
        return

    config = read_autoware_ego_vtype_config()
    apply_vtype_config_to_state("autoware_ego", config)
    st.session_state.autoware_battery_failure_threshold = float(
        config.get("battery_failure_threshold", 0.0) or 0.0
    )
    st.session_state.autoware_ego_config_loaded = True
    st.session_state.autoware_ego_config_version = current_version


def reset_vtype_model_state(prefix, emission_model):
    attributes, parameters = ego_model_defaults(emission_model)

    for key, value in attributes.items():
        st.session_state[f"{prefix}_attr_{key}"] = value
    for key, value in parameters.items():
        st.session_state[f"{prefix}_param_{key}"] = value


def bounded_float(value, minimum, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum

    return min(max(number, minimum), maximum)


def parameter_input_grid(values, key_prefix, text_area_keys=()):
    text_area_keys = set(text_area_keys)
    result = {}
    normal_items = [(key, value) for key, value in values.items() if key not in text_area_keys]
    cols = st.columns(3)

    for index, (key, value) in enumerate(normal_items):
        widget_key = f"{key_prefix}_{key}"

        with cols[index % len(cols)]:
            if key == "color":
                current_color = st.session_state.get(widget_key, value)
                if current_color not in BASE_EGO_COLORS:
                    current_color = "white"
                st.session_state[widget_key] = current_color
                result[key] = st.selectbox(
                    key,
                    options=BASE_EGO_COLORS,
                    index=edge_select_index(BASE_EGO_COLORS, current_color),
                    key=widget_key,
                )
            elif key in EGO_NUMERIC_LIMITS:
                minimum, maximum, step = EGO_NUMERIC_LIMITS[key]
                st.session_state[widget_key] = bounded_float(
                    st.session_state.get(widget_key, value),
                    minimum,
                    maximum,
                )
                result[key] = st.number_input(
                    key,
                    min_value=minimum,
                    max_value=maximum,
                    step=step,
                    key=widget_key,
                )
            else:
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = value
                result[key] = st.text_input(key, key=widget_key)

    for key in text_area_keys:
        if key not in values:
            continue

        widget_key = f"{key_prefix}_{key}"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = values[key]

        result[key] = st.text_area(
            key,
            key=widget_key,
            help="Leave empty to use the SUMO default.",
        )

    return result


def render_ego_vehicle_config():
    initialize_ego_config_state()

    carla_vtypes = available_carla_vehicle_types()
    if not carla_vtypes:
        st.error("No CARLA vehicle blueprint found in vtypes.json.")
        return None

    if st.session_state.ego_carla_blueprint not in carla_vtypes:
        st.session_state.ego_carla_blueprint = DEFAULT_EGO_BLUEPRINT

    st.write("##### Ego Vehicle Type")
    top_cols = st.columns([2, 1, 1])
    with top_cols[0]:
        carla_blueprint = st.selectbox(
            "CARLA vType / blueprint",
            options=carla_vtypes,
            index=edge_select_index(carla_vtypes, st.session_state.ego_carla_blueprint),
            key="ego_carla_blueprint",
        )
    with top_cols[1]:
        emission_model = st.selectbox(
            "Emission model",
            options=[ENERGY_EMISSION_CLASS, MMPEVEM_EMISSION_CLASS],
            key="ego_emission_model",
        )
    with top_cols[2]:
        battery_capacity = st.number_input(
            "Max battery capacity [Wh]",
            min_value=1.0,
            max_value=500000.0,
            value=float(st.session_state.ego_max_battery_capacity),
            step=100.0,
            key="ego_max_battery_capacity",
        )

    if st.session_state.ego_last_emission_model != emission_model:
        reset_vtype_model_state("ego", emission_model)
        st.session_state.ego_last_emission_model = emission_model

    attribute_defaults, parameter_defaults = ego_model_defaults(emission_model)

    with st.expander("Ego vType parameters", expanded=False):
        st.caption(
            "Empty parameters are omitted from the XML file, so SUMO uses its own defaults."
        )
        st.write("Attributes")
        attributes = parameter_input_grid(attribute_defaults, "ego_attr")
        st.write("Parameters")
        parameters = parameter_input_grid(
            parameter_defaults,
            "ego_param",
            text_area_keys=("powerLossMap",),
        )

    if st.button("Save ego vType XML"):
        write_ego_vtype_config(
            carla_blueprint,
            emission_model,
            battery_capacity,
            attributes=attributes,
            parameters=parameters,
        )
        st.success("egovtype.xml updated.")

    return {
        "sumo_vtype": EGO_SUMO_VTYPE,
        "carla_blueprint": carla_blueprint,
        "emission_model": emission_model,
        "battery_capacity": battery_capacity,
        "attributes": attributes,
        "parameters": parameters,
        "emission_class": ego_emission_class_value(emission_model),
    }


def render_autoware_ego_vtype_editor():
    initialize_autoware_ego_config_state()

    st.subheader("🔧 Ego vType")
    st.caption(
        f"The Autoware Docker launch currently expects the CARLA blueprint `{AUTOWARE_EGO_VTYPE}`."
    )
    if st.session_state.autoware_last_launch:
        last_launch = st.session_state.autoware_last_launch
        st.caption(
            f"Last Autoware launch: map `{last_launch.get('map_name', '-')}`, "
            f"container `{last_launch.get('container_name', '-')}`."
        )
    selected_map_name, _ = apply_selected_runtime_map()
    st.caption(
        f"Autoware launch map fixed to `{selected_map_name}` from step 1."
    )
    autoware_edges = get_offline_edges(selected_map_name)
    autoware_edge_ids = [edge.edge_id for edge in autoware_edges]
    autoware_labels = {
        edge.edge_id: edge_label(edge)
        for edge in autoware_edges
    }
    autoware_edge_options = [""] + autoware_edge_ids
    if st.session_state.autoware_start_edge not in autoware_edge_ids:
        st.session_state.autoware_start_edge = (
            st.session_state.start_edge
            if st.session_state.start_edge in autoware_edge_ids
            else None
        )
    if st.session_state.autoware_goal_edge not in autoware_edge_ids:
        st.session_state.autoware_goal_edge = (
            st.session_state.end_edge
            if st.session_state.end_edge in autoware_edge_ids
            else None
        )
    scenario_result = st.session_state.traffic_generation_result
    traffic_target_edge = (
        getattr(scenario_result, "target_edge", "")
        if scenario_result is not None and getattr(scenario_result, "target_edge", "")
        else st.session_state.traffic_target_edge
    )
    if traffic_target_edge not in autoware_edge_ids:
        traffic_target_edge = ""
    sync_process = st.session_state.traffic_process
    sync_running = sync_process is not None and sync_process.poll() is None
    sync_waiting_for_autoware = waiting_for_autoware_sync()
    sumo_gui_enabled = bool(st.session_state.traffic_sumo_gui)
    autoware_delay = effective_autoware_startup_wait_seconds(sumo_gui_enabled)

    top_cols = st.columns([2, 1, 1])
    with top_cols[0]:
        st.text_input(
            "SUMO/CARLA vehicle type",
            value=AUTOWARE_EGO_VTYPE,
            key="autoware_ego_carla_blueprint",
            disabled=True,
        )
    with top_cols[1]:
        emission_model = st.selectbox(
            "Emission model",
            options=[ENERGY_EMISSION_CLASS, MMPEVEM_EMISSION_CLASS],
            key="autoware_ego_emission_model",
        )
    with top_cols[2]:
        battery_capacity = st.number_input(
            "Max battery capacity [Wh]",
            min_value=1.0,
            max_value=500000.0,
            value=float(st.session_state.autoware_ego_max_battery_capacity),
            step=100.0,
            key="autoware_ego_max_battery_capacity",
        )

    if st.session_state.autoware_ego_initial_battery > battery_capacity:
        st.session_state.autoware_ego_initial_battery = battery_capacity

    if st.session_state.autoware_battery_failure_threshold > battery_capacity:
        st.session_state.autoware_battery_failure_threshold = battery_capacity

    battery_cols = st.columns(2)
    with battery_cols[0]:
        battery_charge_level = st.slider(
            "Current battery charge [Wh]",
            min_value=0.0,
            max_value=float(battery_capacity),
            step=max(1.0, float(battery_capacity) / 100.0),
            key="autoware_ego_initial_battery",
            help="Saved as `device.battery.chargeLevel` in the active vtypes.json.",
        )
    with battery_cols[1]:
        battery_failure_threshold = st.number_input(
            "Critical battery threshold [Wh]",
            min_value=0.0,
            max_value=float(battery_capacity),
            value=float(st.session_state.autoware_battery_failure_threshold),
            step=max(1.0, float(battery_capacity) / 100.0),
            key="autoware_battery_failure_threshold",
            help=(
                "If the Autoware ego battery drops below this threshold, the dashboard "
                "requests a stop and cancels the active route."
            ),
        )

    battery_threshold_valid = battery_charge_level > battery_failure_threshold
    if not battery_threshold_valid:
        st.warning(
            "The current battery must be greater than the critical threshold "
            "to avoid an immediate stop."
        )

    if st.session_state.autoware_ego_last_emission_model != emission_model:
        reset_vtype_model_state("autoware_ego", emission_model)
        st.session_state.autoware_ego_last_emission_model = emission_model

    # Autoware Mini is a ROS 1 stack. Start and goal edges are converted into a
    # ROS initial pose and a ROS navigation goal after the docker launch starts.
    st.write("### Autoware Route")
    st.caption(
        "Select the route exactly like in the scenario step: click the map, choose the edge direction, "
        "or reuse the current congestion/source/destination edges with the quick actions below."
    )
    all_x = [point[0] for edge in autoware_edges for point in edge.shape]
    all_y = [point[1] for edge in autoware_edges for point in edge.shape]
    center_x = (min(all_x) + max(all_x)) / 2
    center_y = (min(all_y) + max(all_y)) / 2

    route_map = folium.Map(
        location=[center_y, center_x],
        zoom_start=1,
        crs="Simple",
        tiles=None,
    )
    for edge in autoware_edges:
        color = "#2563eb"
        weight = 4
        if edge.edge_id == traffic_target_edge:
            color = "#f97316"
            weight = 7
        if edge.edge_id == st.session_state.autoware_start_edge:
            color = "#16a34a"
            weight = 8
        elif edge.edge_id == st.session_state.autoware_goal_edge:
            color = "#dc2626"
            weight = 8

        coords = [to_map_coords(point[0], point[1]) for point in edge.shape]
        folium.PolyLine(
            coords,
            color=color,
            weight=weight,
            tooltip=edge.edge_id,
        ).add_to(route_map)

    if st.session_state.autoware_last_click:
        click_x, click_y = st.session_state.autoware_last_click
        folium.CircleMarker([click_y, click_x], radius=5, color="black", fill=True).add_to(route_map)

    route_map_data = st_folium(
        route_map,
        use_container_width=True,
        height=420,
        key=f"autoware_route_map_{selected_map_name}",
    )

    if route_map_data and route_map_data.get("last_clicked"):
        click_y = route_map_data["last_clicked"]["lat"]
        click_x = route_map_data["last_clicked"]["lng"]
        st.session_state.autoware_last_click = (click_x, click_y)

    if st.session_state.autoware_last_click:
        click_x, click_y = st.session_state.autoware_last_click
        candidate, distance = nearest_edge(autoware_edges, click_x, click_y)
        direction_options = edge_direction_options(autoware_edges, candidate.edge_id)
        if st.session_state.autoware_clicked_direction not in direction_options:
            st.session_state.autoware_clicked_direction = candidate.edge_id

        st.write(
            f"Nearest edge to click: `{candidate.edge_id}` "
            f"({distance:.1f} m)"
        )
        clicked_edge = st.selectbox(
            "Clicked edge direction",
            options=direction_options,
            format_func=lambda value: autoware_labels[value],
            key="autoware_clicked_direction",
        )

        click_cols = st.columns(4)
        with click_cols[0]:
            if st.button("Use as START", key="autoware_set_start_edge"):
                st.session_state.autoware_start_edge = clicked_edge
                st.rerun()
        with click_cols[1]:
            if st.button("Use as END", key="autoware_set_goal_edge"):
                st.session_state.autoware_goal_edge = clicked_edge
                st.rerun()
        with click_cols[2]:
            st.write("")
        with click_cols[3]:
            st.write("")
    else:
        st.info("Click on the map to select an Autoware edge.")

    edge_cols = st.columns(2)
    with edge_cols[0]:
        selected_start_edge = st.selectbox(
            "Autoware start edge",
            options=autoware_edge_options,
            index=edge_select_index(
                autoware_edge_options,
                st.session_state.autoware_start_edge or "",
            ),
            format_func=lambda value: "Select a start edge" if not value else autoware_labels[value],
        )
    with edge_cols[1]:
        selected_goal_edge = st.selectbox(
            "Autoware goal edge",
            options=autoware_edge_options,
            index=edge_select_index(
                autoware_edge_options,
                st.session_state.autoware_goal_edge or "",
            ),
            format_func=lambda value: "Select a goal edge" if not value else autoware_labels[value],
        )

    st.session_state.autoware_start_edge = selected_start_edge or None
    st.session_state.autoware_goal_edge = selected_goal_edge or None

    if st.session_state.autoware_start_edge and st.session_state.autoware_goal_edge:
        st.caption(
            "Autoware edge route: "
            f"`{st.session_state.autoware_start_edge}` -> `{st.session_state.autoware_goal_edge}`"
        )
    else:
        st.caption(
            "If start and goal edges are left empty, Autoware still launches but the route must be set manually in RViz."
        )

    if traffic_target_edge:
        st.caption(f"Current congestion edge: `{traffic_target_edge}`")

    route_action_cols = st.columns(6)
    start_opposite = (
        opposite_edge_id(st.session_state.autoware_start_edge, set(autoware_edge_ids))
        if st.session_state.autoware_start_edge else None
    )
    goal_opposite = (
        opposite_edge_id(st.session_state.autoware_goal_edge, set(autoware_edge_ids))
        if st.session_state.autoware_goal_edge else None
    )
    with route_action_cols[0]:
        if st.button(
            "Use congestion START",
            key="autoware_quick_congestion_start",
            disabled=not traffic_target_edge,
        ):
            st.session_state.autoware_start_edge = traffic_target_edge
            st.rerun()
    with route_action_cols[1]:
        if st.button(
            "Use congestion END",
            key="autoware_quick_congestion_end",
            disabled=not traffic_target_edge,
        ):
            st.session_state.autoware_goal_edge = traffic_target_edge
            st.rerun()
    with route_action_cols[2]:
        if st.button(
            "Use scenario START",
            key="autoware_use_scenario_start",
            disabled=st.session_state.start_edge not in autoware_edge_ids,
        ):
            st.session_state.autoware_start_edge = st.session_state.start_edge
            st.rerun()
    with route_action_cols[3]:
        if st.button(
            "Use scenario END",
            key="autoware_use_scenario_end",
            disabled=st.session_state.end_edge not in autoware_edge_ids,
        ):
            st.session_state.autoware_goal_edge = st.session_state.end_edge
            st.rerun()
    with route_action_cols[4]:
        if st.button("Invert START", key="autoware_invert_start", disabled=not start_opposite):
            st.session_state.autoware_start_edge = start_opposite
            st.rerun()
    with route_action_cols[5]:
        if st.button("Invert END", key="autoware_invert_end", disabled=not goal_opposite):
            st.session_state.autoware_goal_edge = goal_opposite
            st.rerun()

    st.number_input(
        "Autoware planner speed cap [km/h]",
        min_value=5.0,
        max_value=130.0,
        value=50.0,
        step=1.0,
        key="autoware_planner_speed_limit_kmh",
        help=(
            "Autoware Mini uses map speed limits only if the Lanelet2 map contains them. "
            "These Town01/Town04/Town05 maps currently do not, so this value acts as the effective route speed cap."
        ),
    )
    st.caption(
        "The current Lanelet2 Town maps do not expose per-lane `speed_limit` or `speed_ref` tags, "
        "so the planner falls back to the configured global cap loaded at Autoware startup."
    )

    attribute_defaults, parameter_defaults = ego_model_defaults(emission_model)

    with st.expander("Autoware ego vType parameters", expanded=False):
        st.caption(
            "This updates the SUMO/vtypes metadata associated with the Autoware ego vehicle."
        )
        st.write("Attributes")
        attributes = parameter_input_grid(attribute_defaults, "autoware_ego_attr")
        st.write("Parameters")
        parameters = parameter_input_grid(
            parameter_defaults,
            "autoware_ego_param",
            text_area_keys=("powerLossMap",),
        )

    st.info(
        "If CARLA does not have the UT Lexus asset imported, the Docker launch will fail before spawning the ego vehicle."
    )
    if scenario_result is None:
        st.caption("Generate a SUMO scenario in step 2 before starting the synchronized launch.")
    else:
        gui_label = "enabled" if st.session_state.traffic_sumo_gui else "disabled"
        st.caption(
            f"Step 3 will reuse the running CARLA instance on map `{scenario_result.map_name}` "
            f"with SUMO GUI {gui_label}."
        )
    if sync_waiting_for_autoware:
        st.info(
            "SUMO/CARLA is already armed from step 3 and waiting for Autoware. "
            "Click `Run Autoware` to start the warm-up and then release the simulation."
        )
    if sumo_gui_enabled:
        st.caption(
            "SUMO GUI is enabled, so the Autoware startup wait is disabled and the simulation "
            "is released immediately when you click `Run Autoware`."
        )
    else:
        st.caption(
            f"The configured Autoware startup wait is `{autoware_delay}s` and starts when you click `Run Autoware`."
        )

    action_cols = st.columns(2)
    with action_cols[0]:
        save_clicked = st.button("Save ego vType in vtypes.json")
    with action_cols[1]:
        launch_clicked = st.button(
            "Run Autoware",
            disabled=(sync_running and not sync_waiting_for_autoware) or not battery_threshold_valid,
        )

    if save_clicked or launch_clicked:
        autoware_vtype_params = dict(parameters)
        autoware_vtype_params["dashboard.battery.failureThreshold"] = str(
            float(battery_failure_threshold)
        )
        write_autoware_ego_vtype_config(
            emission_model,
            battery_capacity,
            battery_charge_level,
            attributes=attributes,
            parameters=autoware_vtype_params,
        )
        if save_clicked:
            st.success(f"`{AUTOWARE_EGO_VTYPE}` updated in vtypes.json.")

    if launch_clicked:
        selected_start_edge = st.session_state.autoware_start_edge
        selected_goal_edge = st.session_state.autoware_goal_edge
        if bool(selected_start_edge) != bool(selected_goal_edge):
            st.error("Select both the Autoware start edge and the Autoware goal edge.")
            return {
                "sumo_vtype": AUTOWARE_EGO_VTYPE,
                "carla_blueprint": AUTOWARE_EGO_VTYPE,
                "emission_model": emission_model,
                "battery_capacity": battery_capacity,
                "battery_charge_level": battery_charge_level,
                "attributes": attributes,
                "parameters": parameters,
                "emission_class": ego_emission_class_value(emission_model),
            }
        try:
            started_at = time.time()
            launch = launch_autoware_carla_in_container(
                selected_map_name,
                start_edge=selected_start_edge,
                goal_edge=selected_goal_edge,
                speed_limit_kmh=float(st.session_state.autoware_planner_speed_limit_kmh),
            )
            st.session_state.autoware_last_launch = {
                "map_name": selected_map_name,
                "container_name": launch.get("container_name"),
                "command": launch.get("command"),
                "started_at": started_at,
                "startup_wait_seconds": autoware_delay,
                "start_edge": selected_start_edge,
                "goal_edge": selected_goal_edge,
                "speed_limit_kmh": float(st.session_state.autoware_planner_speed_limit_kmh),
                "battery_failure_threshold": float(battery_failure_threshold),
                "planner_speed_limit_setup": launch.get("planner_speed_limit_setup"),
                "route_publication_error": launch.get("route_publication_error"),
            }
            st.session_state.autoware_active_battery_failure_threshold = float(
                battery_failure_threshold
            )
        except Exception as exc:
            st.error(f"Autoware start failed: {exc}")
            return {
                "sumo_vtype": AUTOWARE_EGO_VTYPE,
                "carla_blueprint": AUTOWARE_EGO_VTYPE,
                "emission_model": emission_model,
                "battery_capacity": battery_capacity,
                "battery_charge_level": battery_charge_level,
                "attributes": attributes,
                "parameters": parameters,
                "emission_class": ego_emission_class_value(emission_model),
            }

        st.success(
            f"Autoware launch started in container `{launch['container_name']}` "
            f"for map `{selected_map_name}`."
        )
        st.caption(f"Host prep: `{launch['host_command']}` with `DISPLAY={launch['display']}`")
        st.caption(f"Executed: `{launch['command']}`")
        if selected_start_edge and selected_goal_edge:
            st.caption(
                f"ROS route: `{selected_start_edge}` -> `{selected_goal_edge}`"
            )
        initial_pose_data = launch.get("initial_pose") or {}
        goal_pose_data = launch.get("goal_pose") or {}
        if initial_pose_data and goal_pose_data:
            st.caption(
                "Resolved ROS poses with "
                f"`{initial_pose_data.get('projection_mode')}` projection."
            )
        st.caption(
            f"Planner speed cap: `{float(st.session_state.autoware_planner_speed_limit_kmh):.0f} km/h`."
        )
        st.caption(
            f"Critical battery threshold: `{float(battery_failure_threshold):.1f} Wh`."
        )
        planner_speed_limit_setup = launch.get("planner_speed_limit_setup") or {}
        if planner_speed_limit_setup.get("planning_yaml"):
            st.caption(
                "Planner config written to "
                f"`{planner_speed_limit_setup['planning_yaml']}` before `roslaunch`."
            )
        if launch.get("route_publication_error"):
            st.error(
                "Autoware launched, but publishing `/initialpose` and "
                f"`/move_base_simple/goal` failed: {launch['route_publication_error']}"
            )
            return {
                "sumo_vtype": AUTOWARE_EGO_VTYPE,
                "carla_blueprint": AUTOWARE_EGO_VTYPE,
                "emission_model": emission_model,
                "battery_capacity": battery_capacity,
                "battery_charge_level": battery_charge_level,
                "attributes": attributes,
                "parameters": parameters,
                "emission_class": ego_emission_class_value(emission_model),
            }
        if sync_waiting_for_autoware:
            try:
                spinner_message = (
                    "Releasing the SUMO/CARLA simulation immediately after the Autoware launch..."
                    if autoware_delay == 0
                    else (
                        f"Waiting {autoware_delay}s for Autoware startup, then releasing the "
                        "SUMO/CARLA simulation..."
                    )
                )
                with st.spinner(spinner_message):
                    time.sleep(max(0, autoware_delay))
                    if not waiting_for_autoware_sync():
                        raise RuntimeError(
                            "SUMO/CARLA is no longer waiting for Autoware. "
                            "The synchronization process may have stopped."
                        )
                    release_waiting_synchronization_gate()
                st.success("Autoware warm-up completed. SUMO/CARLA simulation released.")
            except Exception as exc:
                st.error(f"Autoware started, but the SUMO release failed: {exc}")
        else:
            if autoware_delay == 0:
                st.caption(
                    "Warm-up wait is disabled. Step 3 can start the simulation immediately."
                )
            else:
                st.caption(
                    f"Warm-up timer started now. Step 3 can start the simulation after `{autoware_delay}s`."
                )

    return {
        "sumo_vtype": AUTOWARE_EGO_VTYPE,
        "carla_blueprint": AUTOWARE_EGO_VTYPE,
        "emission_model": emission_model,
        "battery_capacity": battery_capacity,
        "battery_charge_level": battery_charge_level,
        "attributes": attributes,
        "parameters": parameters,
        "emission_class": ego_emission_class_value(emission_model),
    }


def get_live_sumo_vehicles():
    response = requests.get(f"{API_URL}/vehicles", timeout=2)
    if response.status_code != 200:
        raise RuntimeError(response.text)
    return response.json().get("vehicles", [])


def is_carla_spawned_vehicle(vehicle):
    vehicle_id = str(vehicle.get("id", ""))
    type_id = str(vehicle.get("type_id", ""))
    return vehicle_id.startswith("carla") or type_id == "vehicle.lexus.utlexus"


def vehicle_display_label(vehicle):
    battery_state = "battery" if vehicle.get("has_battery_device") else "no battery"
    return (
        f"{vehicle.get('id', '-')} | type={vehicle.get('type_id', '-')} | "
        f"edge={vehicle.get('edge', '-')} | {battery_state}"
    )


def preferred_monitoring_vehicle_id(vehicles):
    for vehicle in vehicles:
        if is_carla_spawned_vehicle(vehicle):
            return vehicle["id"]

    for vehicle in vehicles:
        if vehicle.get("id") == "ego_vehicle":
            return vehicle["id"]

    return vehicles[0]["id"] if vehicles else None


def fetch_live_vehicle_vtype_config(veh_id):
    encoded_vehicle_id = quote(str(veh_id), safe="")
    response = requests.get(f"{API_URL}/vehicle/{encoded_vehicle_id}", timeout=2)
    if response.status_code != 200:
        raise RuntimeError(response.text)
    return response.json()


def initialize_live_vehicle_config_state(veh_id):
    current_version = active_carla_version()
    if (
        st.session_state.live_vehicle_config_loaded_for == veh_id
        and st.session_state.live_vehicle_config_version == current_version
    ):
        return

    config = fetch_live_vehicle_vtype_config(veh_id)
    apply_vtype_config_to_state("live_vehicle", config)
    st.session_state.live_vehicle_config_loaded_for = veh_id
    st.session_state.live_vehicle_config_version = current_version


def render_live_vehicle_vtype_config(veh_id):
    initialize_live_vehicle_config_state(veh_id)

    current_type_id = st.session_state.get("live_vehicle_sumo_vtype", "")
    has_battery_device = bool(st.session_state.get("live_vehicle_has_battery_device"))
    if current_type_id:
        st.caption(f"Current SUMO vType: `{current_type_id}`")
    st.caption(
        "The update changes only SUMO vType data for this vehicle. "
        "Route and CARLA blueprint stay unchanged."
    )

    top_cols = st.columns([2, 1, 1])
    with top_cols[0]:
        st.text_input(
            "CARLA vType / blueprint",
            value=st.session_state.live_vehicle_carla_blueprint,
            key="live_vehicle_carla_blueprint",
            disabled=True,
        )
    with top_cols[1]:
        emission_model = st.selectbox(
            "Emission model",
            options=[ENERGY_EMISSION_CLASS, MMPEVEM_EMISSION_CLASS],
            key="live_vehicle_emission_model",
        )
    with top_cols[2]:
        battery_capacity = st.number_input(
            "Max battery capacity [Wh]",
            min_value=1.0,
            max_value=500000.0,
            value=float(st.session_state.live_vehicle_max_battery_capacity),
            step=100.0,
            key="live_vehicle_max_battery_capacity",
            disabled=not has_battery_device,
        )

    if st.session_state.live_vehicle_last_emission_model != emission_model:
        reset_vtype_model_state("live_vehicle", emission_model)
        st.session_state.live_vehicle_last_emission_model = emission_model

    attribute_defaults, parameter_defaults = ego_model_defaults(emission_model)

    with st.expander("Live vType parameters", expanded=False):
        st.caption(
            "Only vType data is edited here. Path, route, and departure remain unchanged."
        )
        st.write("Attributes")
        attributes = parameter_input_grid(attribute_defaults, "live_vehicle_attr")
        st.write("Parameters")
        parameters = parameter_input_grid(
            parameter_defaults,
            "live_vehicle_param",
            text_area_keys=("powerLossMap",),
        )

    return {
        "vehicle_id": veh_id,
        "sumo_vtype": current_type_id,
        "carla_blueprint": st.session_state.live_vehicle_carla_blueprint,
        "emission_model": emission_model,
        "battery_capacity": battery_capacity,
        "attributes": attributes,
        "parameters": parameters,
        "emission_class": ego_emission_class_value(emission_model),
        "has_battery_device": has_battery_device,
    }


def resolve_ego_route_from_congestion(
    edges,
    selected_start,
    selected_end,
    target_edge,
    route_mode,
    traffic_source_edge=None,
    traffic_destination_edge=None,
):
    start_edge = selected_start
    end_edge = selected_end
    via_edge = None
    auto_fields = []

    if route_mode == EGO_ROUTE_TO_CONGESTION:
        end_edge = target_edge
        if not start_edge or start_edge == end_edge:
            start_edge = pick_auto_edge(
                edges,
                excluded={target_edge},
                preferred=(traffic_source_edge,),
            )
            if start_edge:
                auto_fields.append("start")

    elif route_mode == EGO_ROUTE_FROM_CONGESTION:
        start_edge = target_edge
        if not end_edge or end_edge == start_edge:
            end_edge = pick_auto_edge(
                edges,
                excluded={target_edge},
                preferred=(traffic_destination_edge,),
            )
            if end_edge:
                auto_fields.append("destination")

    else:
        via_edge = target_edge
        if not start_edge:
            start_edge = pick_auto_edge(
                edges,
                excluded={target_edge, end_edge},
                preferred=(traffic_source_edge,),
            )
            if start_edge:
                auto_fields.append("start")

        if not end_edge:
            end_edge = pick_auto_edge(
                edges,
                excluded={target_edge, start_edge},
                preferred=(traffic_destination_edge,),
            )
            if end_edge:
                auto_fields.append("destination")

    return start_edge, end_edge, via_edge, auto_fields


def render_traffic_scenario(show_runner=True):
    st.subheader("🚦 Traffic Scenario")

    maps = available_maps()
    if not maps:
        st.error("No SUMO map found in examples/net.")
        return

    map_name, _ = apply_selected_runtime_map()
    st.caption(
        f"Scenario Town fixed to `{map_name}` from step 1."
    )

    edges = get_offline_edges(map_name)
    edge_ids = [edge.edge_id for edge in edges]
    labels = {edge.edge_id: edge_label(edge) for edge in edges}

    for state_key in (
        "traffic_target_edge",
        "traffic_source_edge",
        "traffic_destination_edge",

    ):
        if st.session_state[state_key] not in edge_ids:
            st.session_state[state_key] = ""

    mode = st.radio(
        "Scenario type",
        ["Congestion Edge", "Random Traffic"],
        horizontal=True,
    )

    st.write("### Map")

    all_x = [point[0] for edge in edges for point in edge.shape]
    all_y = [point[1] for edge in edges for point in edge.shape]
    center_x = (min(all_x) + max(all_x)) / 2
    center_y = (min(all_y) + max(all_y)) / 2

    target_edge = st.session_state.traffic_target_edge
    source_edge = st.session_state.traffic_source_edge
    destination_edge = st.session_state.traffic_destination_edge


    m = folium.Map(
        location=[center_y, center_x],
        zoom_start=1,
        crs="Simple",
        tiles=None,
    )

    for edge in edges:
        color = "#2563eb"
        weight = 4

        if edge.edge_id == target_edge:
            color = "#dc2626"
            weight = 8
        elif edge.edge_id == source_edge:
            color = "#9333ea"
            weight = 7
        elif edge.edge_id == destination_edge:
            color = "#16a34a"
            weight = 8


        coords = [to_map_coords(point[0], point[1]) for point in edge.shape]
        folium.PolyLine(
            coords,
            color=color,
            weight=weight,
            tooltip=edge.edge_id,
        ).add_to(m)

    if st.session_state.traffic_last_click:
        x, y = st.session_state.traffic_last_click
        folium.CircleMarker([y, x], radius=5, color="black", fill=True).add_to(m)

    map_data = st_folium(
        m,
        use_container_width=True,
        height=460,
        key=f"traffic_map_{map_name}",
    )

    if map_data and map_data.get("last_clicked"):
        y = map_data["last_clicked"]["lat"]
        x = map_data["last_clicked"]["lng"]
        st.session_state.traffic_last_click = (x, y)

    if st.session_state.traffic_last_click:
        x, y = st.session_state.traffic_last_click
        candidate, distance = nearest_edge(edges, x, y)
        direction_options = edge_direction_options(edges, candidate.edge_id)
        if st.session_state.traffic_clicked_direction not in direction_options:
            st.session_state.traffic_clicked_direction = candidate.edge_id

        st.write(
            f"Nearest edge to click: `{candidate.edge_id}` "
            f"({distance:.1f} m)"
        )

        clicked_edge = st.selectbox(
            "Clicked edge direction",
            options=direction_options,
            format_func=lambda value: labels[value],
            key="traffic_clicked_direction",
        )

        click_cols = st.columns(3)
        with click_cols[0]:
            if st.button("Use as congestion"):
                st.session_state.traffic_target_edge = clicked_edge
                st.rerun()
        with click_cols[1]:
            if st.button("Use as source"):
                st.session_state.traffic_source_edge = clicked_edge
                st.rerun()
        with click_cols[2]:
            if st.button("Use as destination"):
                st.session_state.traffic_destination_edge = clicked_edge
                st.rerun()

    else:
        st.info("Click on the map to select an edge.")

    st.write("### Parameters")

    empty_label = "Select by clicking on the map or on the list"
    target_options = [""] + edge_ids
    target_selection = st.selectbox(
        "Edge to congestion",
        options=target_options,
        index=edge_select_index(target_options, st.session_state.traffic_target_edge),
        format_func=lambda value: empty_label if not value else labels[value],
        disabled=mode == "Random Traffic",
    )

    source_options = [""] + edge_ids
    source_selection = st.selectbox(
        "Source Edge (optional)",
        options=source_options,
        index=edge_select_index(source_options, st.session_state.traffic_source_edge),
        format_func=lambda value: "Random over the whole map" if not value else labels[value],
        disabled=mode == "Random Traffic",
    )

    destination_selection = st.selectbox(
        "Destination Edge (optional)",
        options=target_options,
        index=edge_select_index(target_options, st.session_state.traffic_destination_edge),
        format_func=lambda value: "Random over the whole map" if not value else labels[value],
        disabled=mode == "Random Traffic",
    )



    st.session_state.traffic_target_edge = target_selection
    st.session_state.traffic_source_edge = source_selection
    st.session_state.traffic_destination_edge = destination_selection


    if mode != "Random Traffic":
        edge_id_set = set(edge_ids)
        direction_cols = st.columns(3)
        target_opposite = (
            opposite_edge_id(target_selection, edge_id_set)
            if target_selection else None
        )
        source_opposite = (
            opposite_edge_id(source_selection, edge_id_set)
            if source_selection else None
        )
        destination_opposite = (
            opposite_edge_id(destination_selection, edge_id_set)
            if destination_selection else None
        )


        with direction_cols[0]:
            if st.button(
                "Invert congestion",
                disabled=not target_opposite,
            ):
                st.session_state.traffic_target_edge = target_opposite
                st.rerun()
        with direction_cols[1]:
            if st.button(
                "Invert source",
                disabled=not source_opposite,
            ):
                st.session_state.traffic_source_edge = source_opposite
                st.rerun()
        with direction_cols[2]:
            if st.button(
                "Invert destination",
                disabled=not destination_opposite,
            ):
                st.session_state.traffic_destination_edge = destination_opposite
                st.rerun()



    param_cols = st.columns(4)
    with param_cols[0]:
        vehicle_count = st.number_input(
            "Vehicles Number",
            min_value=1,
            max_value=5000,
            value=150,
            step=10,
        )
    with param_cols[1]:
        begin = st.number_input("Start spawn at t[s]", min_value=0.0, value=0.0, step=1.0)
    with param_cols[2]:
        end = st.number_input("Stop spawn at t[s]", min_value=0.0, value=120.0, step=1.0)
    with param_cols[3]:
        seed = st.number_input("Seed", min_value=0, max_value=999999, value=42, step=1)

    spawn_pattern = st.selectbox(
        "Spawn distribution",
        ["Equidistant", "Randomly", "All together"],
        disabled=mode == "Random Traffic",
    )

    vtype_options = get_sumo_vtypes()
    if not vtype_options:
        st.error("No SUMO vType found in carlavtypes/egovtype files.")
        return

    st.write("##### Vehicle Type")
    vtype_cols = st.columns([1, 3])
    with vtype_cols[0]:
        random_vehicle_type = st.checkbox("Random vType", value=False)
    with vtype_cols[1]:
        vehicle_type = st.selectbox(
            "SUMO vType",
            options=vtype_options,
            index=edge_select_index(vtype_options, DEFAULT_VEHICLE_TYPE),
            disabled=random_vehicle_type,
        )

    if random_vehicle_type:
        st.caption(
            f"Each vehicle will use a random vType among {len(vtype_options)} available types."
        )

    if mode == "Congestion Edge" and target_selection:
        st.info(
            "Source and destination are optional. If left blank, "
            "generate random traffic but only keep the routes that pass through the congested edge."
        )

    can_generate = mode == "Random Traffic" or bool(target_selection)
    if not can_generate:
        st.warning("Select the edge to congestion.")

    if st.button("Generate route and custom sumocfg", disabled=not can_generate):
        try:
            if mode == "Congestion Edge":
                result = generate_congestion_scenario(
                    map_name=map_name,
                    target_edge=target_selection,
                    destination_edge=destination_selection or None,
                    vehicle_count=int(vehicle_count),
                    begin=float(begin),
                    end=float(end),
                    spawn_pattern=spawn_pattern,
                    source_edge=source_selection or None,
                    seed=int(seed),
                    vehicle_type=vehicle_type,
                    random_vehicle_type=random_vehicle_type,
                    vehicle_types=vtype_options,
                )
            else:
                result = generate_random_trips_scenario(
                    map_name=map_name,
                    vehicle_count=int(vehicle_count),
                    begin=float(begin),
                    end=float(end),
                    seed=int(seed),
                    vehicle_type=vehicle_type,
                    random_vehicle_type=random_vehicle_type,
                    vehicle_types=vtype_options,
                )

            st.session_state.traffic_generation_result = result
            st.success(
                f"Generated {result.generated_count}/{result.requested_count} vehicles."
            )
        except Exception as exc:
            st.error(f"Generation failed: {exc}")

    result = st.session_state.traffic_generation_result
    if result:
        st.write("### Output")
        metric_cols = st.columns(3)
        metric_cols[0].metric("Route Vehicles", result.generated_count)
        metric_cols[1].metric("crossing edge", result.target_count)
        metric_cols[2].metric("Tool", result.mode)

        st.write("Route file:", str(result.route_file))
        st.write("Trips file:", str(result.trip_file))
        st.write("SUMO cfg:", str(result.sumocfg_file))
        st.code(
            "cd " + str(current_sumo_dir()) + "\n" + " ".join(sync_launch_command_for_ui(result.sumocfg_file)),
            language="bash",
        )

        if show_runner:
            render_simulation_runner(result)


def render_simulation_runner(result=None):
    if result is None:
        result = st.session_state.traffic_generation_result

    autoware_workflow = active_carla_version() == "0.9.13"
    st.subheader("▶️ Configure Simulation" if autoware_workflow else "▶️ Run Simulation")
    if result is None:
        st.warning(
            "Generate a SUMO route scenario first in step 2 before starting the co-simulation."
        )
        return

    sync_process = st.session_state.traffic_process
    sync_running = sync_process is not None and sync_process.poll() is None
    carla_server_ready = is_carla_server_ready()
    sync_launch_widget_defaults()

    if autoware_workflow:
        st.caption(
            f"Scenario ready for map `{result.map_name}`. "
            "These settings will be reused in step 4 when the dashboard starts the SUMO/CARLA synchronization."
        )
    else:
        st.caption(
            f"Scenario ready for map `{result.map_name}`. "
            "This step loads the correct Town in CARLA and then starts the SUMO/CARLA synchronization."
        )
    if autoware_workflow:
        st.info(
            "For the Autoware workflow, this step starts the SUMO/CARLA bridge in standby. "
            "Then use step 4 to launch Autoware; after the warm-up, the simulation is released automatically."
        )
        if waiting_for_autoware_sync():
            st.success(
                "SUMO/CARLA bridge is running and waiting for Autoware before advancing simulation time."
            )
            launch_state = autoware_launch_sync_state()
            if launch_state is None:
                st.info("Autoware has not been launched from step 4 yet.")
            elif launch_state["is_ready"]:
                st.success(
                    f"Autoware launched in container `{launch_state['container_name']}`. "
                    "Warm-up completed."
                )
            else:
                st.info(
                    f"Autoware launched in container `{launch_state['container_name']}`. "
                    f"{launch_state['remaining_seconds']:.1f}s of startup wait remain."
                )
        else:
            st.warning("Start simulation here first to arm SUMO/CARLA, then launch Autoware from step 4.")

    sumo_gui = st.checkbox(
        "SUMO GUI",
        key="traffic_sumo_gui_selection",
        help="Disable this to run SUMO headless.",
    )
    if autoware_workflow:
        st.number_input(
            "Autoware startup wait [s]",
            min_value=0,
            max_value=120,
            step=1,
            key="autoware_sync_delay_selection",
            disabled=bool(sumo_gui),
            help=(
                "Delay applied in step 4 before the co-simulation process is started. "
                "Disabled when SUMO GUI is enabled."
            ),
        )
    st.session_state.traffic_carla_mode = "reuse"
    st.session_state.traffic_sumo_gui = bool(st.session_state.traffic_sumo_gui_selection)
    if autoware_workflow:
        st.session_state.autoware_sync_delay_seconds = int(
            st.session_state.autoware_sync_delay_selection
        )
        if sumo_gui:
            st.caption("Autoware startup wait is disabled while SUMO GUI is enabled.")

    if carla_server_ready:
        st.caption(
            f"CARLA server detected on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}. "
            "The dashboard will still load the scenario Town before starting the co-simulation."
        )
    else:
        st.caption(
            f"No CARLA server detected on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}. "
            "Start CARLA from step 1 before running the co-simulation."
        )

    run_cols = st.columns(2)
    with run_cols[0]:
        if st.button(
            "Start simulation" if autoware_workflow else "Run co-simulation",
            disabled=sync_running,
        ):
            try:
                spinner_message = (
                    "Loading the selected Town and arming SUMO/CARLA while waiting for Autoware..."
                    if autoware_workflow
                    else "Loading the selected Town and starting SUMO/co-simulation..."
                )

                with st.spinner(spinner_message):
                    launch = start_dashboard_synchronization_launch(
                        result,
                        carla_mode="reuse",
                        carla_timeout=int(st.session_state.traffic_carla_timeout_seconds),
                        sumo_gui=sumo_gui,
                        wait_for_autoware=autoware_workflow,
                    )
                st.success(
                    synchronization_success_message(
                        launch,
                        result,
                        carla_mode="reuse",
                        sumo_gui=sumo_gui,
                    )
                )
            except Exception as exc:
                st.error(f"Start failed: {exc}")
    with run_cols[1]:
        if st.button("Stop co-simulation", disabled=not sync_running):
            sync_process.terminate()
            st.session_state.traffic_process = None
            clear_waiting_synchronization_state(remove_gate_file=True)
            st.warning("Process stopped.")

    sync_process = st.session_state.traffic_process
    if sync_process is not None and sync_process.poll() is None:
        st.info(f"Co-simulation started, PID {sync_process.pid}.")
    elif sync_process is not None:
        st.info(f"Last process ended with code {sync_process.returncode}.")

    carla_process = st.session_state.carla_process
    if carla_process is not None and carla_process.poll() is None:
        st.info(f"CARLA running, PID {carla_process.pid}.")
    elif carla_server_ready:
        st.info(
            f"CARLA server detected on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}."
        )
    elif carla_process is not None:
        st.info(f"Last CARLA process ended with code {carla_process.returncode}.")

    if st.session_state.traffic_process_log:
        st.caption(f"Co-simulation Log: {st.session_state.traffic_process_log}")
    if st.session_state.carla_process_log:
        st.caption(f"CARLA Log: {st.session_state.carla_process_log}")


def render_setup():
    if not backend_alive:
        st.warning(
            "Backend is not active: you can configure the ego route and vType, "
            "but spawning will only be available after the co-simulation starts."
        )

    traffic_result = st.session_state.traffic_generation_result
    map_name = (
        traffic_result.map_name
        if traffic_result is not None
        else st.session_state.traffic_map_name
    )
    edges = get_offline_edges(map_name)
    edge_ids = [edge.edge_id for edge in edges]
    edge_id_set = set(edge_ids)
    labels = {edge.edge_id: edge_label(edge) for edge in edges}

    if st.session_state.start_edge not in edge_id_set:
        st.session_state.start_edge = None
    if st.session_state.end_edge not in edge_id_set:
        st.session_state.end_edge = None

    # =====================================================
    # MAP (STATIC - NOT REFRESHED LOGICALLY)
    # =====================================================

    st.subheader("🗺️ Network Map (click to select)")
    st.caption(f"Ego map: {map_name}")

    all_x = [point[0] for edge in edges for point in edge.shape]
    all_y = [point[1] for edge in edges for point in edge.shape]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    m = folium.Map(
        location=[center_y, center_x],
        zoom_start=1,
        crs="Simple",
        tiles=None,
    )

    traffic_target_edge = (
        getattr(traffic_result, "target_edge", "")
        if traffic_result is not None and getattr(traffic_result, "target_edge", "")
        else st.session_state.traffic_target_edge
    )

    for edge in edges:
        color = "#2563eb"
        weight = 4

        if edge.edge_id == st.session_state.start_edge:
            color = "#16a34a"
            weight = 8
        elif edge.edge_id == st.session_state.end_edge:
            color = "#dc2626"
            weight = 8
        elif edge.edge_id == traffic_target_edge:
            color = "#f97316"
            weight = 7

        coords = [to_map_coords(point[0], point[1]) for point in edge.shape]
        folium.PolyLine(
            coords,
            color=color,
            weight=weight,
            tooltip=edge.edge_id,
        ).add_to(m)

    # marker persistente
    if st.session_state.get("last_click"):
        x, y = st.session_state.last_click
        folium.CircleMarker([y, x], radius=5, color="red", fill=True).add_to(m)

    map_data = st_folium(
        m,
        use_container_width=True,
        height=500,
        key="network_map",
    )

    # click handling
    if map_data and map_data.get("last_clicked"):
        y = map_data["last_clicked"]["lat"]
        x = map_data["last_clicked"]["lng"]

        st.session_state.last_click = (x, y)

    if st.session_state.get("last_click"):
        x, y = st.session_state.last_click
        candidate, distance = nearest_edge(edges, x, y)
        direction_options = edge_direction_options(edges, candidate.edge_id)
        if st.session_state.ego_clicked_direction not in direction_options:
            st.session_state.ego_clicked_direction = candidate.edge_id

        st.write(f"Clicked SUMO coords: {x:.2f}, {y:.2f}")
        st.write(
            f"Edge closest to point clicked: `{candidate.edge_id}` "
            f"({distance:.1f} m)"
        )

        clicked_edge = st.selectbox(
            "Edge Direction",
            options=direction_options,
            format_func=lambda value: labels[value],
            key="ego_clicked_direction",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Set START", key="set_start_edge"):
                st.session_state.start_edge = clicked_edge
                st.rerun()

        with col2:
            if st.button("Set END", key="set_end_edge"):
                st.session_state.end_edge = clicked_edge
                st.rerun()
    else:
        st.info("Click on the map to select a SUMO coordinate.")

    st.write("Start:", labels.get(st.session_state.start_edge, st.session_state.start_edge))
    st.write("End:", labels.get(st.session_state.end_edge, st.session_state.end_edge))

    direction_cols = st.columns(2)
    start_opposite = (
        opposite_edge_id(st.session_state.start_edge, edge_id_set)
        if st.session_state.start_edge else None
    )
    end_opposite = (
        opposite_edge_id(st.session_state.end_edge, edge_id_set)
        if st.session_state.end_edge else None
    )

    with direction_cols[0]:
        if st.button("Invert START", disabled=not start_opposite):
            st.session_state.start_edge = start_opposite
            st.rerun()
    with direction_cols[1]:
        if st.button("Invert END", disabled=not end_opposite):
            st.session_state.end_edge = end_opposite
            st.rerun()

    # =====================================================
    # SPAWN VEHICLE
    # =====================================================

    st.subheader("🚗 Spawn Ego Vehicle")

    ego_config = render_ego_vehicle_config()
    if ego_config is None:
        return

    max_battery_capacity = float(ego_config["battery_capacity"])
    if st.session_state.ego_initial_battery > max_battery_capacity:
        st.session_state.ego_initial_battery = max_battery_capacity
    if st.session_state.ego_battery_failure_threshold > max_battery_capacity:
        st.session_state.ego_battery_failure_threshold = max_battery_capacity

    battery_cols = st.columns(2)
    with battery_cols[0]:
        battery_init = st.slider(
            "Initial battery [Wh]",
            min_value=0.0,
            max_value=max_battery_capacity,
            step=max(1.0, max_battery_capacity / 100.0),
            key="ego_initial_battery",
        )
    with battery_cols[1]:
        battery_failure_threshold = st.number_input(
            "Critical battery threshold [Wh]",
            min_value=0.0,
            max_value=max_battery_capacity,
            value=float(st.session_state.ego_battery_failure_threshold),
            step=max(1.0, max_battery_capacity / 100.0),
            key="ego_battery_failure_threshold",
            help=(
                "The vehicle is stopped when the remaining battery is "
                "less than or equal to this threshold."
            ),
        )

    battery_threshold_valid = battery_init > battery_failure_threshold
    if not battery_threshold_valid:
        st.warning(
            "The initial battery must be greater than the critical threshold "
            "to avoid an immediate failure."
        )

    congestion_available = bool(
        traffic_result is not None
        and traffic_target_edge
        and traffic_target_edge in edge_id_set
    )
    effective_start_edge = st.session_state.start_edge
    effective_end_edge = st.session_state.end_edge
    via_edge = None
    auto_route_fields = []
    route_hint_start_edge = None
    route_hint_end_edge = None

    if traffic_result is not None:
        route_hint_start_edge, route_hint_end_edge = generated_route_hints(
            traffic_result.route_file,
            traffic_target_edge,
        )

    if congestion_available:
        use_traffic_route = st.checkbox(
            "Use the generated congestion for the ego route",
            key="ego_use_traffic_route",
        )
        if use_traffic_route:
            route_modes = [
                EGO_ROUTE_VIA,
                EGO_ROUTE_FROM_CONGESTION,
                EGO_ROUTE_TO_CONGESTION,
            ]
            if st.session_state.ego_traffic_route_mode not in route_modes:
                st.session_state.ego_traffic_route_mode = route_modes[0]

            route_mode = st.radio(
                "Ego route preference",
                route_modes,
                horizontal=True,
                key="ego_traffic_route_mode",
            )

            (
                effective_start_edge,
                effective_end_edge,
                via_edge,
                auto_route_fields,
            ) = resolve_ego_route_from_congestion(
                edges,
                st.session_state.start_edge,
                st.session_state.end_edge,
                traffic_target_edge,
                route_mode,
                traffic_source_edge=(
                    st.session_state.traffic_source_edge or route_hint_start_edge
                ),
                traffic_destination_edge=(
                    st.session_state.traffic_destination_edge or route_hint_end_edge
                ),
            )

            if route_mode == EGO_ROUTE_VIA:
                st.info(f"The ego route will pass through: {labels[traffic_target_edge]}")
            elif route_mode == EGO_ROUTE_FROM_CONGESTION:
                st.info(f"The ego start edge will be: {labels[traffic_target_edge]}")
            else:
                st.info(f"The ego destination edge will be: {labels[traffic_target_edge]}")

            route_parts = [
                f"START `{effective_start_edge or '-'}`",
                f"END `{effective_end_edge or '-'}`",
            ]
            if via_edge:
                route_parts.insert(1, f"VIA `{via_edge}`")
            st.caption("Effective ego route: " + " -> ".join(route_parts))
            if auto_route_fields:
                st.caption(
                    "Auto-selected edges for: "
                    + ", ".join(auto_route_fields)
                    + "."
                )
    elif traffic_result is not None:
        st.info("No congested edge is available in the generated traffic scenario.")

    if st.button(
        "Spawn Ego Vehicle",
        disabled=not backend_alive or not battery_threshold_valid,
    ):
        if effective_start_edge and effective_end_edge:
            write_ego_vtype_config(
                ego_config["carla_blueprint"],
                ego_config["emission_model"],
                ego_config["battery_capacity"],
                attributes=ego_config["attributes"],
                parameters=ego_config["parameters"],
            )
            vtype_params = {
                "has.battery.device": "true",
                "carla.blueprint": ego_config["carla_blueprint"],
                "device.battery.capacity": str(ego_config["battery_capacity"]),
                "dashboard.battery.failureThreshold": str(battery_failure_threshold),
            }
            vtype_params.update(
                {
                    key: value
                    for key, value in ego_config["parameters"].items()
                    if value is not None and str(value).strip() != ""
                }
            )

            payload = {
                "start": effective_start_edge,
                "end": effective_end_edge,
                "battery": battery_init,
                "battery_failure_threshold": battery_failure_threshold,
                "vtype": ego_config["sumo_vtype"],
                "carla_blueprint": ego_config["carla_blueprint"],
                "vtype_attrs": {
                    **ego_config["attributes"],
                    "emissionClass": ego_config["emission_class"],
                },
                "vtype_params": vtype_params,
            }
            if via_edge and via_edge not in {effective_start_edge, effective_end_edge}:
                payload["via"] = via_edge

            response = requests.post(
                f"{API_URL}/spawn",
                json=payload,
                timeout=2,
            )
            if response.status_code == 200:
                reset_monitoring_trip_state()
                st.session_state.monitoring = False
                st.session_state.ego_active_start_edge = effective_start_edge
                st.session_state.ego_active_end_edge = effective_end_edge
                st.session_state.ego_active_via_edge = via_edge
                st.session_state.ego_active_battery_failure_threshold = (
                    battery_failure_threshold
                )
                st.success("Ego vehicle spawned")
            else:
                st.error(f"Spawn failed: {response.text}")
        else:
            if st.session_state.ego_use_traffic_route and congestion_available:
                st.warning(
                    "I could not resolve an ego route automatically: "
                    "select at least a start edge or an end edge."
                )
            else:
                st.warning("Select start and end edges first")


def render_live_vehicle_editor():
    st.subheader("🔧 Live Vehicle vType")

    if not backend_alive:
        st.warning(
            "Backend not active: start the co-simulation first to inspect and edit live SUMO vehicles."
        )
        return

    try:
        vehicles = get_live_sumo_vehicles()
    except Exception as exc:
        st.error(f"Could not load SUMO vehicles: {exc}")
        return

    vehicles = [vehicle for vehicle in vehicles if is_carla_spawned_vehicle(vehicle)]
    if not vehicles:
        st.info("No CARLA-spawned SUMO vehicle is currently active in the simulation.")
        return

    vehicle_ids = [vehicle["id"] for vehicle in vehicles]
    vehicle_labels = {vehicle["id"]: vehicle_display_label(vehicle) for vehicle in vehicles}

    if st.session_state.live_vehicle_selected_id not in vehicle_ids:
        st.session_state.live_vehicle_selected_id = vehicle_ids[0]
        st.session_state.live_vehicle_config_loaded_for = None

    selector_cols = st.columns([3, 1])
    with selector_cols[0]:
        selected_vehicle_id = st.selectbox(
            "SUMO vehicle",
            options=vehicle_ids,
            format_func=lambda veh_id: vehicle_labels[veh_id],
            key="live_vehicle_selected_id",
        )
    with selector_cols[1]:
        st.write("")
        if st.button("Refresh vehicle list"):
            st.rerun()

    st.caption(
        "Only CARLA-spawned SUMO vehicles are listed here. "
        "The current route is left untouched."
    )

    try:
        live_vehicle_config = render_live_vehicle_vtype_config(selected_vehicle_id)
    except Exception as exc:
        st.error(f"Could not load vehicle vType data: {exc}")
        st.session_state.live_vehicle_config_loaded_for = None
        return

    if live_vehicle_config is None:
        return

    if not live_vehicle_config.get("has_battery_device", False):
        st.info(
            "This vehicle has no SUMO battery device. Live update will still change the "
            "vehicle type data, but battery-specific fields stay inactive."
        )

    if st.button("Apply live vType update"):
        vtype_params = {
            "has.battery.device": "true",
            "carla.blueprint": live_vehicle_config["carla_blueprint"],
            "device.battery.capacity": str(live_vehicle_config["battery_capacity"]),
        }
        vtype_params.update(
            {
                key: value
                for key, value in live_vehicle_config["parameters"].items()
                if value is not None and str(value).strip() != ""
            }
        )

        payload = {
            "emission_model": live_vehicle_config["emission_model"],
            "battery_capacity": live_vehicle_config["battery_capacity"],
            "vtype_attrs": {
                **live_vehicle_config["attributes"],
                "emissionClass": live_vehicle_config["emission_class"],
            },
            "vtype_params": vtype_params,
        }
        encoded_vehicle_id = quote(str(selected_vehicle_id), safe="")
        try:
            response = requests.post(
                f"{API_URL}/vehicle/{encoded_vehicle_id}/vtype",
                json=payload,
                timeout=3,
            )
        except Exception as exc:
            st.error(f"Live update failed: {exc}")
            return

        if response.status_code == 200:
            updated_vehicle = response.json().get("vehicle", {})
            if updated_vehicle:
                apply_vtype_config_to_state("live_vehicle", updated_vehicle)
                st.session_state.live_vehicle_config_loaded_for = selected_vehicle_id
                st.session_state.live_vehicle_config_version = active_carla_version()
            st.success(f"Live vType updated for `{selected_vehicle_id}`.")
        else:
            st.error(f"Live update failed: {response.text}")


simulation_step = simulation_step_label()
vehicle_step = vehicle_setup_step_label()
autoware_workflow = active_carla_version() == "0.9.13"
if autoware_workflow:
    section_options = [
        STEP_CARLA_LABEL,
        STEP_ROUTES_LABEL,
        simulation_step,
        vehicle_step,
        STEP_MONITORING_LABEL,
    ]
    workflow_caption = (
        "Follow the workflow from left to right: start CARLA, generate SUMO routes, "
        "configure the run, then launch Autoware and start the co-simulation."
    )
else:
    section_options = [
        STEP_CARLA_LABEL,
        STEP_ROUTES_LABEL,
        vehicle_step,
        simulation_step,
        STEP_MONITORING_LABEL,
    ]
    workflow_caption = (
        "Follow the workflow from left to right: start CARLA, generate SUMO routes, "
        "prepare the vehicle, then run the co-simulation."
    )
current_section = st.session_state.get("dashboard_section")
if current_section not in section_options:
    mapped_section = None
    if current_section:
        current_title = current_section.split(". ", 1)[-1]
        if "Simulation" in current_title:
            mapped_section = simulation_step
        elif "Autoware" in current_title or "SUMO Ego Vehicle" in current_title:
            mapped_section = vehicle_step
    st.session_state.dashboard_section = mapped_section or STEP_CARLA_LABEL
elif current_section is None:
    st.session_state.dashboard_section = STEP_CARLA_LABEL

section = st.segmented_control(
    "Execution steps",
    section_options,
    default=STEP_CARLA_LABEL,
    key="dashboard_section",
    label_visibility="collapsed",
)

st.caption(
    workflow_caption
)

if section == STEP_CARLA_LABEL:
        preserve_scroll_position("dashboard_carla_step_scroll_position")
        render_carla_step()
elif section == STEP_ROUTES_LABEL:
        preserve_scroll_position("dashboard_routes_step_scroll_position")
        render_traffic_scenario(show_runner=False)
elif section == simulation_step:
        preserve_scroll_position("dashboard_simulation_step_scroll_position")
        render_simulation_runner()
elif section == vehicle_step:
        preserve_scroll_position("dashboard_vehicle_step_scroll_position")
        if active_carla_version() == "0.9.13":
            render_autoware_ego_vtype_editor()
        else:
            render_setup()
else:
        render_monitoring()
