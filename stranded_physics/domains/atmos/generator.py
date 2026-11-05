"""Recorded weather windows and constant user dials."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from stranded_physics.core.api import InterfaceError, TimeAxis
from stranded_physics.core.records import load_parameters, load_datasets
from .model import Atmos, HERE, RAW, SECONDS_PER_HOUR

ISLANDS = ("st_vincent", "la_palma", "miyakejima", "montserrat", "stromboli")
PARAMETERS = load_parameters(HERE / "generator_params.toml")
P = {p.id.split(".")[-1]: p for p in PARAMETERS}


def validate(name, value):
    p = P[name]
    if not np.isfinite(value) or not p.valid[0].magnitude <= value <= p.valid[1].magnitude:
        raise InterfaceError(f"{name} outside valid range")


class WeatherWindow(Atmos):
    parameters = PARAMETERS

    def __init__(self, time: TimeAxis, island: str, month: int | None = None, files=None):
        if island not in ISLANDS:
            raise InterfaceError("unknown weather island")
        if month is not None and (not isinstance(month, (int, np.integer)) or not 1 <= month <= 12):
            raise InterfaceError("month must be 1 to 12")
        if (not isinstance(time.n, (int, np.integer)) or time.n < 1 or not np.isfinite(time.dt_s)
                or time.dt_s <= 0 or time.dt_s % SECONDS_PER_HOUR
                or time.t0_utc.minute or time.t0_utc.second or time.t0_utc.microsecond):
            raise InterfaceError("weather window needs a whole-hour axis")
        self.time, self.island, self.month = time, island, month
        year = int(P["year"].value.magnitude)
        self.start = datetime(year,1,1,tzinfo=timezone.utc)
        end = datetime(year+1,1,1,tzinfo=timezone.utc)
        span = (time.n-1)*time.dt_s
        if not np.isfinite(span) or span > (end-self.start).total_seconds()-SECONDS_PER_HOUR:
            raise InterfaceError("weather axis cannot fit inside 2023")
        latest = end-timedelta(hours=1,seconds=span)
        self.starts = tuple(self.start+timedelta(hours=h) for h in range(max(0,int((latest-self.start).total_seconds()/SECONDS_PER_HOUR)+1))
                            if month is None or (self.start+timedelta(hours=h)).month == month)
        if not self.starts:
            raise InterfaceError("weather axis cannot fit inside 2023")
        records = {r.id:r for r in load_datasets(HERE / "datasets.toml", "atmos")}
        self.files = files if files is not None else {role:(RAW/(name+".json"),records[name].sha256)
                       for role,name in (("surface","surface_decade_"+island),("upper","upper_wind_2023_"+island))}

    def check_validity(self, fields):
        # Check coverage of the full selectable range, without consuming randomness.
        reasons = []
        for start in (self.starts[0],self.starts[-1]):
            reasons.extend(Atmos(TimeAxis(start,self.time.dt_s,self.time.n),self.files).check_validity(fields))
        return sorted(set(reasons))

    def run(self, fields, rng):
        reasons = self.check_validity(fields)
        if reasons:
            raise InterfaceError("; ".join(reasons))
        self.window_start_utc = self.starts[int(rng.integers(len(self.starts)))]
        selected = TimeAxis(self.window_start_utc,self.time.dt_s,self.time.n)
        # Keep output metadata on the scenario axis while reading the sampled dates.
        class Remap:
            def put(inner, name, data, unit, grid=None, time=None):
                fields.put(name,data,unit,grid=grid,time=self.time)
        return Atmos(selected,self.files).run(Remap(),rng)


class WeatherDials:
    id, tier, inputs = "atmos", "T0", ()
    outputs, parameters = Atmos.outputs, PARAMETERS

    def __init__(self,time: TimeAxis,rain_mm_h,wind_m_s,wind_bearing_deg,temperature_c,upper_wind_m_s,upper_bearing_deg):
        self.time = time
        values = dict(rain=rain_mm_h,wind=wind_m_s,bearing=wind_bearing_deg,temperature=temperature_c,upper_wind=upper_wind_m_s,upper_bearing=upper_bearing_deg)
        for name,value in values.items():
            validate(name,value)
        self.values = dict(zip(("rain_rate","wind_speed","wind_bearing","air_temperature","wind_speed_500hpa","wind_bearing_500hpa","wind_speed_200hpa","wind_bearing_200hpa"),(rain_mm_h,wind_m_s,wind_bearing_deg,temperature_c,upper_wind_m_s,upper_bearing_deg,upper_wind_m_s,upper_bearing_deg)))
        if self.check_validity(None):
            raise InterfaceError("invalid weather dial time axis")

    def check_validity(self,fields):
        return [] if isinstance(self.time.n,(int,np.integer)) and self.time.n>0 and np.isfinite(self.time.dt_s) and self.time.dt_s>0 else ["invalid time axis"]

    def run(self,fields,rng):
        for output in self.outputs:
            fields.put(output.name,np.full(self.time.n,self.values[output.name.split(".")[-1]]),output.unit,time=self.time)
        return {}
