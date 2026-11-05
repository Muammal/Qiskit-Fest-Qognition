"""Seeded synthetic volcanic islands; geometry is not calibrated to real relief."""
from pathlib import Path
import csv
import heapq
import numpy as np
from stranded_physics.core.api import InterfaceError, GridSpec, XY
from stranded_physics.core.records import load_parameters
from .model import Terrain, static_zones
from .drainage import route, flow_accumulation, height_above_drainage

HERE = Path(__file__).resolve().parent
PARAMETERS = load_parameters(HERE / "generator_params.toml")
P = {p.id.split(".")[-1]: p for p in PARAMETERS}
S = {k: float(p.value.magnitude) for k, p in P.items()}


def validate(name, value):
    p = P[name]
    if not np.isfinite(value) or not p.valid[0].magnitude <= value <= p.valid[1].magnitude:
        raise InterfaceError(f"{name} outside valid range")


def sample_island(rng) -> tuple[float, float]:
    with (HERE.parents[2] / "disaster_data/catalog/volcanoes.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = []
        for row in csv.DictReader(f):
            if row["island_class"] not in ("small_island", "large_island"):
                continue
            try:
                summit, area = float(row["elevation_m"]), float(row["island_area_km2"])
                validate("summit", summit)
                validate("area", area)
            except (ValueError, TypeError):
                continue
            rows.append((summit, area))
    if not rows:
        raise InterfaceError("no eligible catalogue islands")
    return rows[int(rng.integers(len(rows)))]


class GeneratedTerrain:
    id, tier, inputs = "terrain", "T1", ()
    outputs = Terrain.outputs
    parameters = PARAMETERS

    def __init__(self, grid: GridSpec, centre: XY, summit_m: float, area_km2: float, vent: XY | None = None):
        validate("summit", summit_m)
        validate("area", area_km2)
        self.grid, self.centre, self.summit_m, self.area_km2, self.vent = grid, centre, summit_m, area_km2, vent

    def check_validity(self, fields):
        g = self.grid
        if g.dx_m <= 0 or min(g.nx, g.ny) < 3 or not np.isfinite(self.centre).all():
            return ["invalid island grid or centre"]
        radius = np.sqrt(self.area_km2 * 1e6 / np.pi) * (1 + S["coast"]) / (1 - S["coast"])
        clearance = min(self.centre[0]-g.x0_m, g.x0_m+g.nx*g.dx_m-self.centre[0], g.y0_m-self.centre[1], self.centre[1]-(g.y0_m-g.ny*g.dx_m))
        count = round(self.area_km2 * 1e6 / g.dx_m**2)
        if clearance <= radius + g.dx_m or count < 1 or abs(count*g.dx_m**2/1e6/self.area_km2-1) > S["area_tolerance"]:
            return ["island cannot fit on this grid with sea around its edge and requested area precision"]
        return []

    def run(self, fields, rng):
        reasons = self.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        g = self.grid
        x, y = np.meshgrid(g.x0_m+(np.arange(g.nx)+.5)*g.dx_m-self.centre[0], g.y0_m-(np.arange(g.ny)+.5)*g.dx_m-self.centre[1])
        r, theta = np.hypot(x,y), np.arctan2(y,x)
        phases = rng.uniform(0, 2*np.pi, int(S["modes"]))
        coast = sum(np.sin((i+2)*theta+p) for i,p in enumerate(phases)) / len(phases)
        metric = r / (1 + S["coast"]*coast)
        # Connected priority growth enforces one island even on coarse grids.
        start = np.unravel_index(np.argmin(r), r.shape)
        heap, seen = [(float(metric[start]), *start)], {start}
        land = np.zeros(r.shape, bool)
        count = round(self.area_km2*1e6/g.dx_m**2)
        for _ in range(count):
            _, row, col = heapq.heappop(heap)
            if row in (0,g.ny-1) or col in (0,g.nx-1):
                raise InterfaceError("island cannot fit with an enclosing sea")
            land[row,col] = True
            for dr,dc in ((0,1),(0,-1),(1,0),(-1,0)):
                cell = row+dr,col+dc
                if 0 <= cell[0] < g.ny and 0 <= cell[1] < g.nx and cell not in seen:
                    seen.add(cell)
                    heapq.heappush(heap,(float(metric[cell]),*cell))
        radius = np.max(metric[land]) + g.dx_m
        valleys = (1 + np.cos(S["valley_modes"]*theta + phases[0])) / 2
        relief = (1-metric/radius) * (1-S["valleys"]*valleys*(1-np.exp(-r/(radius*S["summit_transition"]))))
        elevation = np.where(land, relief, 0.)
        elevation[land] *= self.summit_m / elevation.max()
        self.summit_xy = g.centre(*np.unravel_index(np.argmax(elevation), elevation.shape))
        drainage = route(elevation,land,g.dx_m)
        area = flow_accumulation(drainage,land,g.dx_m)
        cover = np.where(land,np.where(elevation>S["bare_height"],S["bare_code"],S["tree_code"]),S["sea_code"])
        arrays = (elevation,land.astype(float),cover,static_zones(g,self.vent if self.vent is not None else self.summit_xy),area,height_above_drainage(elevation,drainage,area,S["channel_area"]))
        for output,data in zip(self.outputs,arrays):
            fields.put(output.name,data,output.unit,g)
        return {}
