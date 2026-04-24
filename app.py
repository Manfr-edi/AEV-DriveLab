import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import folium
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from streamlit_folium import st_folium
from urllib.parse import quote

from sumo_route_tools import (
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
    current_sumo_dir,
    ego_emission_class_value,
    ego_model_defaults,
    edge_label,
    edge_direction_options,
    generate_congestion_scenario,
    generate_random_trips_scenario,
    is_carla_server_ready,
    nearest_edge,
    opposite_edge_id,
    read_ego_vtype_config,
    read_autoware_ego_vtype_config,
    read_sumo_edges,
    set_active_carla_version,
    start_synchronization,
    launch_autoware_carla_in_container,
    write_ego_vtype_config,
    write_autoware_ego_vtype_config,
)

API_URL = "http://localhost:5000"
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

st.title("🚗 EV Digital Twin Dashboard")

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
    "traffic_carla_mode": None,
    "selected_carla_version": None,
    "applied_carla_version": None,
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
        default_version = active_carla_version()
        if default_version not in versions:
            default_version = versions[-1]
        st.session_state.selected_carla_version = default_version

    control_cols = st.columns([1.2, 3])
    with control_cols[0]:
        selected_version = st.selectbox(
            "CARLA version",
            options=versions,
            key="selected_carla_version",
        )
    with control_cols[1]:
        st.caption(
            "Generated SUMO files, Town loading, and co-simulation startup use the selected "
            f"installation: CARLA_{selected_version}."
        )

    previous_version = st.session_state.applied_carla_version
    set_active_carla_version(selected_version)
    if previous_version not in (None, selected_version):
        st.session_state.traffic_generation_result = None
        st.session_state.ego_config_loaded = False
        st.session_state.ego_config_version = None
        st.session_state.autoware_ego_config_loaded = False
        st.session_state.autoware_ego_config_version = None
        st.session_state.live_vehicle_config_loaded_for = None
        st.session_state.live_vehicle_config_version = None

    st.session_state.applied_carla_version = selected_version
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


def reset_monitoring_trip_state():
    st.session_state.battery_data = []
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
            else 0.0
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
        else 0.0
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

    destination_edge = st.session_state.ego_active_end_edge or st.session_state.end_edge
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
        st.warning("First Run `run_dashboard_synchronization.py' from Traffic Scenario tab.")
        return

    try:
        live_vehicles = get_live_sumo_vehicles()
    except Exception as exc:
        st.error(f"Could not load vehicles for monitoring: {exc}")
        return

    monitoring_candidates = [
        vehicle
        for vehicle in live_vehicles
        if vehicle.get("id") == "ego_vehicle" or is_carla_spawned_vehicle(vehicle)
    ]
    if not monitoring_candidates:
        st.info("No ego or CARLA-spawned SUMO vehicle is currently active.")
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
        if st.button("Start Monitoring"):
            st.session_state.monitoring = True
            st.session_state.last_monitoring_poll = 0.0
            if st.session_state.monitoring_started_at is None:
                st.session_state.monitoring_started_at = time.time()

    with col2:
        if st.button("Stop Monitoring"):
            st.session_state.monitoring = False

    chart_placeholder = st.empty()
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
                update_vehicle_events(res)

            try:
                st.session_state.monitoring_events = requests.get(
                    f"{API_URL}/events",
                    timeout=1,
                ).json()
            except Exception:
                pass

            st.session_state.last_monitoring_poll = now

    if st.session_state.battery_data:
        df = pd.DataFrame(st.session_state.battery_data, columns=["battery"])
        chart_placeholder.line_chart(df)

    res = st.session_state.latest_monitoring_state
    if res:
        raw_battery = res.get("battery")
        try:
            battery_val = float(raw_battery) if raw_battery is not None else None
        except (TypeError, ValueError):
            battery_val = None
        speed = res.get("speed", 0)
        edge = res.get("edge", "-")
        vehicle_id = res.get("vehicle_id", selected_vehicle_id)

        with metrics_placeholder.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🚘 Vehicle", vehicle_id)
            c2.metric("🔋 Battery", "-" if battery_val is None else battery_val)
            c3.metric("🚗 Speed", speed)
            c4.metric("🛣️ Edge", edge)

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
        f"Edit `{AUTOWARE_EGO_VTYPE}` in the active `data/vtypes.json` before Autoware spawns the vehicle."
    )
    selected_map_name = st.session_state.traffic_map_name
    st.caption(
        f"Autoware launch map: `{selected_map_name}`. "
        "This uses the map currently selected in the Traffic Scenario tab."
    )

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

    battery_charge_level = st.slider(
        "Current battery charge [Wh]",
        min_value=0.0,
        max_value=float(battery_capacity),
        step=max(1.0, float(battery_capacity) / 100.0),
        key="autoware_ego_initial_battery",
        help="Saved as `device.battery.chargeLevel` in the active vtypes.json.",
    )

    if st.session_state.autoware_ego_last_emission_model != emission_model:
        reset_vtype_model_state("autoware_ego", emission_model)
        st.session_state.autoware_ego_last_emission_model = emission_model

    attribute_defaults, parameter_defaults = ego_model_defaults(emission_model)

    with st.expander("Autoware ego vType parameters", expanded=False):
        st.caption(
            "This writes the base electric vehicle definition used when Autoware creates `vehicle.lexus.utlexus`."
        )
        st.write("Attributes")
        attributes = parameter_input_grid(attribute_defaults, "autoware_ego_attr")
        st.write("Parameters")
        parameters = parameter_input_grid(
            parameter_defaults,
            "autoware_ego_param",
            text_area_keys=("powerLossMap",),
        )

    action_cols = st.columns(2)
    with action_cols[0]:
        save_clicked = st.button("Save ego vType in vtypes.json")
    with action_cols[1]:
        launch_clicked = st.button("Run Autoware in Docker")

    if save_clicked or launch_clicked:
        write_autoware_ego_vtype_config(
            emission_model,
            battery_capacity,
            battery_charge_level,
            attributes=attributes,
            parameters=parameters,
        )
        if save_clicked:
            st.success(f"`{AUTOWARE_EGO_VTYPE}` updated in vtypes.json.")

    if launch_clicked:
        try:
            launch = launch_autoware_carla_in_container(selected_map_name)
            st.success(
                f"Autoware launch started in container `{launch['container_name']}` "
                f"for map `{selected_map_name}`."
            )
            st.caption(f"Executed: `{launch['command']}`")
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


def render_traffic_scenario():
    st.subheader("🚦 Traffic Scenario")

    maps = available_maps()
    if not maps:
        st.error("No SUMO map found in examples/net.")
        return

    if st.session_state.traffic_map_name not in maps:
        st.session_state.traffic_map_name = DEFAULT_MAP if DEFAULT_MAP in maps else maps[0]

    map_name = st.selectbox(
        "Offline map",
        options=maps,
        key="traffic_map_name",
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
            "cd " + str(current_sumo_dir()) + "\n" + " ".join(result.command),
            language="bash",
        )

        sync_process = st.session_state.traffic_process
        sync_running = sync_process is not None and sync_process.poll() is None
        carla_process = st.session_state.carla_process
        managed_carla_running = carla_process is not None and carla_process.poll() is None
        carla_server_ready = is_carla_server_ready()

        if st.session_state.traffic_carla_mode is None:
            st.session_state.traffic_carla_mode = "reuse" if carla_server_ready else "prepare"

        carla_mode = st.radio(
            "CARLA startup mode",
            options=["reuse", "prepare"],
            format_func=lambda mode: {
                "reuse": "Use running CARLA (only start SUMO)",
                "prepare": "Start CARLA and load the Town",
            }[mode],
            key="traffic_carla_mode",
            horizontal=True,
        )

        if carla_server_ready:
            st.caption(
                f"CARLA server detected on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}. "
                "In 'Use running CARLA' mode the dashboard will only launch the SUMO/co-simulation process."
            )
        else:
            st.caption(
                f"No CARLA server detected on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}. "
                "Use 'Start CARLA and load the Town' or start CARLA manually first."
            )

        ensure_carla = carla_mode == "prepare"
        carla_timeout = st.number_input(
            "Timeout CARLA run [s]",
            min_value=30,
            max_value=300,
            value=120,
            step=10,
            disabled=not ensure_carla,
        )

        run_cols = st.columns(3)
        with run_cols[0]:
            if st.button("Run co-simulation", disabled=sync_running):
                try:
                    if carla_mode == "reuse" and not carla_server_ready:
                        raise RuntimeError(
                            f"CARLA is not reachable on {DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}. "
                            "Start CARLA first or switch to 'Start CARLA and load the Town'."
                        )

                    spinner_message = (
                        "Starting SUMO/co-simulation with the running CARLA instance..."
                        if carla_mode == "reuse"
                        else "Setting up CARLA and starting co-simulation..."
                    )

                    with st.spinner(spinner_message):
                        launch = start_synchronization(
                            result.sumocfg_file,
                            map_name=result.map_name,
                            ensure_carla=ensure_carla,
                            carla_process=carla_process,
                            carla_timeout=int(carla_timeout),
                        )

                    st.session_state.traffic_process = launch.sync_process
                    st.session_state.traffic_process_log = launch.sync_log_file
                    st.session_state.carla_process = launch.carla_process
                    st.session_state.carla_process_log = launch.carla_log_file

                    message = f"Co-simulation started, PID {launch.sync_process.pid}."
                    if carla_mode == "reuse":
                        message += (
                            f" Using CARLA already running on "
                            f"{DEFAULT_CARLA_HOST}:{DEFAULT_CARLA_PORT}."
                        )
                    else:
                        if launch.carla_started:
                            message += " CARLA started."
                        if launch.map_loaded:
                            message += f" Town {result.map_name} loaded."
                    st.success(message)
                except Exception as exc:
                    st.error(f"Start failed: {exc}")
        with run_cols[1]:
            if st.button("Stop co-simulation", disabled=not sync_running):
                sync_process.terminate()
                st.session_state.traffic_process = None
                st.warning("Process stopped.")
        with run_cols[2]:
            if st.button("Stop CARLA", disabled=not managed_carla_running):
                carla_process.terminate()
                st.session_state.carla_process = None
                st.warning("CARLA stopped.")

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


section = st.segmented_control(
    "Sezione dashboard",
    ["🚦 Traffic Scenario", "🗺️ Path Setup", "🔧 Ego vType", "📊 Monitoring"],
    default="🚦 Traffic Scenario",
    key="dashboard_section",
    label_visibility="collapsed",
)


if section == "🚦 Traffic Scenario":
        preserve_scroll_position("dashboard_traffic_scroll_position")
        render_traffic_scenario()
elif section == "🗺️ Path Setup":
        preserve_scroll_position("dashboard_setup_scroll_position")
        render_setup()
elif section == "🔧 Ego vType":
        preserve_scroll_position("dashboard_ego_vtype_scroll_position")
        render_autoware_ego_vtype_editor()
else:
        render_monitoring()
