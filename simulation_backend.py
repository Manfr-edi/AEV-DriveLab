import traci
import subprocess
import time

from config import SUMO_BINARY, SUMO_CONFIG
from ego_controller import stop_if_needed

class SimulationManager:
    def __init__(self):
        self.running = False

    def start(self):
        if self.running:
            return

        traci.start([
            SUMO_BINARY,
            "-c", SUMO_CONFIG,
            "--start"
        ])

        self.running = True
        print("✅ Simulation started")

    def step(self):
        if not self.running:
            raise RuntimeError("Simulation not started")

        traci.simulationStep()
        stop_if_needed()

    def close(self):
        if self.running:
            traci.close()
            self.running = False
