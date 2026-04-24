#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  ./setup_carla.sh [<CARLA_DIR> [0.9.13|0.9.15]]

What it does:
  - installs the project-specific SUMO/CARLA files into a vanilla CARLA folder
  - writes the version-specific `vtypes.json`
  - writes the version-specific `egovtype.xml`
  - patches the runtime-critical `bridge_helper.py`
  - patches the runtime-critical `sumo_simulation.py`
  - patches `create_sumo_vtypes.py` so generated SUMO vTypes keep nested params
  - replaces any remaining `bak_carlavtypes.rou.xml` references with `carlavtypes.rou.xml`

Notes:
  - `custom_<Town>.sumocfg` files are not required beforehand; the dashboard generates them.
  - the script creates backups under `<CARLA_DIR>/.customcosim-backups/<timestamp>/`.
  - if `<CARLA_DIR>` is omitted, the script auto-detects `CARLA_0.9.13` / `CARLA_0.9.15`
    folders inside this repository and bootstraps all the ones it finds.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

info() {
    echo "[setup_carla] $*"
}

require_dir() {
    local path="$1"
    [[ -d "$path" ]] || die "Directory not found: $path"
}

require_file() {
    local path="$1"
    [[ -f "$path" ]] || die "File not found: $path"
}

detect_version() {
    local carla_dir="$1"
    local explicit_version="${2:-}"

    if [[ -n "$explicit_version" ]]; then
        case "$explicit_version" in
            0.9.13|0.9.15)
                echo "$explicit_version"
                return 0
                ;;
            *)
                die "Unsupported CARLA version: $explicit_version"
                ;;
        esac
    fi

    local base_name
    base_name="$(basename "$carla_dir")"
    case "$base_name" in
        *0.9.13*)
            echo "0.9.13"
            return 0
            ;;
        *0.9.15*)
            echo "0.9.15"
            return 0
            ;;
    esac

    local dist_dir="$carla_dir/PythonAPI/carla/dist"
    if [[ -d "$dist_dir" ]]; then
        if compgen -G "$dist_dir/carla-*0.9.13*" >/dev/null; then
            echo "0.9.13"
            return 0
        fi
        if compgen -G "$dist_dir/carla-*0.9.15*" >/dev/null; then
            echo "0.9.15"
            return 0
        fi
    fi

    die "Could not infer CARLA version from '$carla_dir'. Pass 0.9.13 or 0.9.15 explicitly."
}

backup_file() {
    local target="$1"
    if [[ ! -f "$target" ]]; then
        return 0
    fi

    local relative_path="${target#$CARLA_DIR/}"
    local backup_target="$BACKUP_DIR/$relative_path"
    mkdir -p "$(dirname "$backup_target")"
    cp -a "$target" "$backup_target"
}

install_file() {
    local source="$1"
    local target="$2"
    local label="$3"

    require_file "$source"
    mkdir -p "$(dirname "$target")"
    backup_file "$target"
    cp "$source" "$target"
    info "Installed $label -> $target"
}

replace_carlavtypes_reference() {
    local target_file="$1"
    if [[ ! -f "$target_file" ]]; then
        return 0
    fi

    python3 - "$target_file" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
updated = text.replace("bak_carlavtypes.rou.xml", "carlavtypes.rou.xml")
if updated != text:
    path.write_text(updated, encoding="utf-8")
PY
}

verify_contains() {
    local target="$1"
    local pattern="$2"
    local label="$3"
    if ! grep -q "$pattern" "$target"; then
        die "Verification failed for $label: pattern '$pattern' not found in $target"
    fi
}

bootstrap_carla_dir() {
    local input_dir="$1"
    local requested_version="${2:-}"

    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    CARLA_DIR="$(cd -- "$input_dir" && pwd)"
    VERSION="$(detect_version "$CARLA_DIR" "$requested_version")"
    TEMPLATE_DIR="$SCRIPT_DIR/bootstrap_templates/$VERSION"
    COMMON_TEMPLATE_DIR="$SCRIPT_DIR/bootstrap_templates/common"
    TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
    BACKUP_DIR="$CARLA_DIR/.customcosim-backups/$TIMESTAMP"

    SUMO_DIR="$CARLA_DIR/Co-Simulation/Sumo"
    EXAMPLES_DIR="$SUMO_DIR/examples"
    DATA_DIR="$SUMO_DIR/data"
    SUMO_INTEGRATION_DIR="$SUMO_DIR/sumo_integration"
    UTIL_DIR="$SUMO_DIR/util"

    VTYPES_JSON="$DATA_DIR/vtypes.json"
    EGO_VTYPE_XML="$EXAMPLES_DIR/egovtype.xml"
    CARLAVTYPES_XML="$EXAMPLES_DIR/carlavtypes.rou.xml"
    VIEWSETTINGS_XML="$EXAMPLES_DIR/viewsettings.xml"
    BRIDGE_HELPER_PY="$SUMO_INTEGRATION_DIR/bridge_helper.py"
    SUMO_SIMULATION_PY="$SUMO_INTEGRATION_DIR/sumo_simulation.py"
    CREATE_SUMO_VTYPES_PY="$UTIL_DIR/create_sumo_vtypes.py"

    require_dir "$CARLA_DIR"
    require_dir "$SUMO_DIR"
    require_dir "$EXAMPLES_DIR"
    require_dir "$DATA_DIR"
    require_dir "$SUMO_INTEGRATION_DIR"
    require_dir "$UTIL_DIR"
    require_dir "$EXAMPLES_DIR/net"
    require_file "$VTYPES_JSON"
    require_file "$CARLAVTYPES_XML"
    require_file "$VIEWSETTINGS_XML"
    require_file "$BRIDGE_HELPER_PY"
    require_file "$SUMO_SIMULATION_PY"
    require_file "$CREATE_SUMO_VTYPES_PY"
    require_file "$TEMPLATE_DIR/vtypes.json"
    require_file "$TEMPLATE_DIR/egovtype.xml"
    require_file "$COMMON_TEMPLATE_DIR/bridge_helper.py"
    require_file "$COMMON_TEMPLATE_DIR/sumo_simulation.py"
    require_file "$COMMON_TEMPLATE_DIR/create_sumo_vtypes.py"

    mkdir -p "$BACKUP_DIR"
    info "Target CARLA dir: $CARLA_DIR"
    info "Detected version: $VERSION"
    info "Backup dir: $BACKUP_DIR"

    install_file "$TEMPLATE_DIR/vtypes.json" "$VTYPES_JSON" "vtypes.json"
    install_file "$TEMPLATE_DIR/egovtype.xml" "$EGO_VTYPE_XML" "egovtype.xml"
    install_file "$COMMON_TEMPLATE_DIR/bridge_helper.py" "$BRIDGE_HELPER_PY" "bridge_helper.py"
    install_file "$COMMON_TEMPLATE_DIR/sumo_simulation.py" "$SUMO_SIMULATION_PY" "sumo_simulation.py"
    install_file "$COMMON_TEMPLATE_DIR/create_sumo_vtypes.py" "$CREATE_SUMO_VTYPES_PY" "create_sumo_vtypes.py"

    for optional_file in \
        "$SUMO_DIR/routes.rou.xml" \
        "$EXAMPLES_DIR/routes.rou.xml" \
        "$EXAMPLES_DIR/trips.trips.xml"
    do
        backup_file "$optional_file"
        replace_carlavtypes_reference "$optional_file"
    done

    while IFS= read -r -d '' custom_cfg; do
        backup_file "$custom_cfg"
        replace_carlavtypes_reference "$custom_cfg"
        info "Patched carlavtypes reference in $custom_cfg"
    done < <(find "$EXAMPLES_DIR" -maxdepth 1 -type f -name 'custom_*.sumocfg' -print0)

    verify_contains "$VTYPES_JSON" '"vehicle.lexus.utlexus"' "vtypes.json"
    verify_contains "$VTYPES_JSON" '"device.battery.capacity"' "vtypes.json"
    verify_contains "$EGO_VTYPE_XML" 'carla.blueprint' "egovtype.xml"
    verify_contains "$BRIDGE_HELPER_PY" 'setEmissionClass' "bridge_helper.py"
    verify_contains "$SUMO_SIMULATION_PY" 'sumolib.net.readNet' "sumo_simulation.py"
    verify_contains "$CREATE_SUMO_VTYPES_PY" '_split_vtype_specs' "create_sumo_vtypes.py"

    python3 -m py_compile "$BRIDGE_HELPER_PY" "$SUMO_SIMULATION_PY" "$CREATE_SUMO_VTYPES_PY" >/dev/null

    info "Bootstrap completed for $CARLA_DIR."
    info "The dashboard will generate custom_Town*.sumocfg on demand."
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -gt 2 ]]; then
    usage
    exit 1
fi

if [[ $# -ge 1 ]]; then
    bootstrap_carla_dir "$1" "${2:-}"
    exit 0
fi

detected_dirs=()
for version_dir in "$SCRIPT_DIR"/CARLA_0.9.13 "$SCRIPT_DIR"/CARLA_0.9.15; do
    if [[ -d "$version_dir" ]]; then
        detected_dirs+=("$version_dir")
    fi
done

if [[ ${#detected_dirs[@]} -eq 0 ]]; then
    die "No local CARLA_0.9.13 or CARLA_0.9.15 directory found next to setup_carla.sh."
fi

for detected_dir in "${detected_dirs[@]}"; do
    bootstrap_carla_dir "$detected_dir"
done
