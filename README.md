# AEV-DriveLab

Experimental tool for building and running SUMO-CARLA co-simulation scenarios through a Streamlit dashboard. The project starts from the CARLA 0.9.15 SUMO co-simulation scripts and extends them with an interactive control layer for:

- generating SUMO traffic on an offline map;
- creating targeted congestion on a selected SUMO edge;
- starting CARLA, loading the correct Town, and launching SUMO-CARLA synchronization;
- spawning an ego vehicle with initial battery, start edge, destination edge, and optional routing through a congestion point;
- monitoring ego vehicle state, speed, current edge, and battery level.

## Main Components

### Streamlit Frontend

The frontend is implemented in `app.py`.

The dashboard has four sections:

- `Path Setup`: select start/end edges for the ego vehicle, including explicit edge direction selection.
- `Traffic Scenario`: generate SUMO route files for random traffic or edge-based congestion.
- `Ego vType`: edit the Autoware-specific ego vehicle configuration. This tab is enabled only when the selected CARLA version is `0.9.13`.
- `Monitoring`: periodically read ego vehicle state from the Flask backend.

Edge selection is based on the offline SUMO map and displays direction information, for example:

```text
39.0.00 | 720->669 verso est (433,406) -> (571,405)
-39.0.00 | 669->720 verso ovest (571,405) -> (433,406)
```

This avoids selecting the opposite lane direction when generating congestion or routing the ego vehicle.

### SUMO Scenario Generation

Scenario generation logic is implemented in `sumo_route_tools.py`.

This module:

- reads `*.net.xml` maps from the selected CARLA installation (for example `carla/CARLA_0.9.13`, `carla/CARLA_0.9.15`, or the legacy root-level folders);
- extracts drivable SUMO edges;
- computes the nearest edge to a map click;
- generates `.trips.xml` and `.rou.xml` files;
- uses SUMO tools such as `duarouter` and `randomTrips.py`;
- loads available SUMO `vType` entries from the route type files and can assign either a fixed type or a random type per vehicle;
- creates or updates `custom_<Town>.sumocfg`;
- starts CARLA, loads the selected Town, and launches `run_dashboard_synchronization.py`.

For congestion scenarios, only the congestion edge is mandatory. Source and destination edges are optional. If they are not provided, random routes are generated while still forcing traffic through the selected congestion edge. After routing, the final route file is filtered so that only vehicles whose route actually contains the congestion edge are kept.

### Simulation Interaction Backend

The dashboard backend is kept outside CARLA's default `run_synchronization.py`.

The custom additions are:

- an internal Flask server exposed on `localhost:5000`;
- endpoints for ego vehicle spawning, ego state, network data, and nearest-edge lookup;
- root-level `run_dashboard_synchronization.py`, a dashboard-specific runner that starts the Flask backend in a thread alongside the co-simulation loop;
- root-level `dashboard_backend.py`, which contains the Flask API;
- root-level `dashboard_sumo.py`, which contains ego vehicle spawn, ego state, custom vType handling, and CARLA blueprint mapping;
- support for ego routes with a `via` edge, meaning `start -> via -> end`.

Main endpoints:

```text
GET  /state
GET  /network
GET  /edges
POST /nearest_edge
POST /spawn
```

This keeps the CARLA example runner separate from the dashboard-specific API and ego-vehicle logic.

## Generated Files

The dashboard writes generated scenario files to:

```text
<carla_install_dir>/Co-Simulation/Sumo/examples/rou/custom_<Town>_traffic.trips.xml
<carla_install_dir>/Co-Simulation/Sumo/examples/rou/custom_<Town>_traffic.rou.xml
<carla_install_dir>/Co-Simulation/Sumo/examples/custom_<Town>.sumocfg
```

Main log files:

```text
<carla_install_dir>/Co-Simulation/Sumo/examples/output/carla_server.log
<carla_install_dir>/Co-Simulation/Sumo/examples/output/carla_map.log
<carla_install_dir>/Co-Simulation/Sumo/examples/output/run_dashboard_synchronization.log
```

## Tested Environment

This repository is currently tested on:

- Ubuntu `24.04`
- Python `3.8`
- Docker
- Docker Compose
- SUMO `1.26`

## Requirements

The minimum setup used to run the project is:

- Ubuntu/Linux
- Python `3.8`
- Docker and Docker Compose
- SUMO `1.26`, with `sumo`, `sumo-gui`, `duarouter`, and the SUMO Python tools available
- Python packages from `requirements.txt`
- at least one CARLA installation under `carla/`

Install the Python dependencies from the repository root:

```bash
pip install -r requirements.txt
```

If SUMO is installed in the default Ubuntu path, the project should pick it up automatically through `/usr/share/sumo`. If needed, you can still export it explicitly:

```bash
export SUMO_HOME=/usr/share/sumo
```

If the CARLA Python API bundled with your CARLA install is not compatible with the interpreter used to start the dashboard, set a dedicated interpreter before launching the project:

```bash
export CARLA_PYTHON=/path/to/python
```

or per version:

```bash
export CARLA_PYTHON_0_9_13=/path/to/python
export CARLA_PYTHON_0_9_15=/path/to/python
```

That interpreter must be able to import at least `carla`, `flask`, `lxml`, `traci`, `sumolib`, and `setuptools`.

## CARLA Setup

At least one CARLA version is required:

- `CARLA 0.9.13`: use this when you want the Autoware workflow.
  Download: <https://tiny.carla.org/carla-0-9-13-linux>
- `CARLA 0.9.15`: use this when you want the ego vehicle managed by SUMO instead of Autoware.
  Download: <https://tiny.carla.org/carla-0-9-15-linux>

You can install one version only, or both.

After downloading, extract the archives inside the repository `carla/` directory, keeping the original folder names intact:

```text
carla/CARLA_0.9.13
carla/CARLA_0.9.15
```

Do not flatten the extracted directories.

Once at least one CARLA installation is in place, run:

```bash
./setup_carla.sh
```

The script bootstraps the selected CARLA installation(s), installs the project-specific SUMO/CARLA files, and performs the additional setup needed by this repository.

## Autoware Docker Setup

If you want to use the Autoware workflow, the `autoware_mini` Docker container must exist and be available.

First build:

```bash
cd autoware_mini_docker_compose
docker compose up --build
```

If the image/container is already built, you can simply start it again with:

```bash
docker start autoware_mini
```

## Startup

After the CARLA setup is complete, start the dashboard from the repository root:

```bash
streamlit run app.py
```

If the default Streamlit port is already in use:

```bash
streamlit run app.py --server.port 8502
```

Then open the dashboard in the browser, for example:

```text
http://127.0.0.1:8501
```

## Typical Local Startup Sequence

Typical startup sequence on a fresh machine:

1. Install system requirements: Python `3.8`, Docker, Docker Compose, SUMO `1.26`.
2. Install Python packages with `pip install -r requirements.txt`.
3. Download and extract `CARLA 0.9.13` and/or `CARLA 0.9.15` into `carla/`.
4. Run `./setup_carla.sh`.
5. If using Autoware, build/start the Docker container from `autoware_mini_docker_compose/`.
6. Start the dashboard with `streamlit run app.py`.

## Typical Workflow

### 1. Generate Traffic or Congestion

Open `Traffic Scenario`.

1. Select the offline map, for example `Town04`.
2. Select `Congestion Edge`.
3. Click on the map.
4. Select the correct direction of the clicked edge.
5. Click `Use as congestion`.
6. Set vehicle count, spawn interval, and seed.
7. Select a fixed `SUMO vType`, or enable `Random vType` to assign a random available type to each generated vehicle.
8. Leave source and destination empty to generate random traffic that passes through the congestion edge, or set them as additional constraints.
9. Click `Generate route and custom sumocfg`.

The dashboard creates the route file and the `custom_<Town>.sumocfg` file.

### 2. Start the Co-Simulation

In `Traffic Scenario`, after generating a scenario:

1. Make sure the correct `CARLA version` is selected.
2. Start CARLA with the top-right dashboard button if needed, or let the scenario start it for you.
3. Click `Run co-simulation`.

The system runs the following sequence:

```bash
./CarlaUE4.sh
python3 PythonAPI/util/config.py --map <Town>
python3 ../../../run_dashboard_synchronization.py --carla-version <0.9.13|0.9.15> examples/custom_<Town>.sumocfg --sumo-gui
```

Even when a CARLA server is already running, the dashboard still loads the requested Town before launching the SUMO/CARLA synchronization.

The synchronization command is executed from:

```text
<carla_install_dir>/Co-Simulation/Sumo
```

### 3. Spawn the Ego Vehicle

Open `Path Setup`.

1. Click on the map.
2. Select the edge direction.
3. Click `Set START`.
4. Repeat for `Set END`.
5. Set the initial battery.
6. Click `Spawn Ego Vehicle`.

If a congestion scenario has been generated in `Traffic Scenario`, the following option becomes available:

```text
Usa il congestionamento generato per la route ego
```

Available modes:

- `Passa per edge congestionato`: the ego route is built as `start -> congestion edge -> end`.
- `Usa edge congestionato come destinazione`: the congestion edge becomes the ego vehicle destination.

### 4. Monitor the Ego Vehicle

Open `Monitoring`.

From this section you can:

- start or stop polling;
- read battery, speed, and current edge;
- view events such as battery depletion or destination reached.

## Operational Notes

- Do not run multiple instances of `run_dashboard_synchronization.py` using the same Flask port `5000`.
- CARLA must be ready on port `2000` before loading a map. The dashboard waits for this automatically when `Run co-simulation` is used.
- Congestion generation relies on SUMO routing. If the network does not allow a valid path through the selected edge, the final number of generated vehicles may be lower than requested.
- Dashboard-specific backend, SUMO extensions, and launcher live at project root. The CARLA `Co-Simulation/Sumo` folder is used as the runtime working directory but does not contain dashboard code.
