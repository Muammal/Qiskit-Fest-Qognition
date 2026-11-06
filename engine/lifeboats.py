"""The twenty lifeboats: seats, davit stations, launch times and boarding rules.

Launch times are Wormstedt's revised table (https://wormstedt.com/Titanic/revised.html),
which calls them approximate. Boats leave at those times whoever has boarded, so
the number aboard is an outcome of the simulation, never an input.
"""

from engine.flood import BRIDGE_UNDER_STEP, LOAD_STEP, clock_step

STANDARD_SEATS = 65  # Museums Worcestershire, Launching the Lifeboats
COLLAPSIBLE_SEATS = 47  # Museums Worcestershire, Launching the Lifeboats
CUTTER_SEATS = 40  # assumption: widely repeated figure; no source could be opened to confirm it
CREW_SEATS = 3  # assumption: rowers assigned per boat
BASE_LOAD_PER_STEP = 3  # assumption: boarding without anyone organising it
LOAD_PER_ORGANISER = 4  # assumption: boarding added by each officer or evacuation worker present
MAX_LOAD_PER_STEP = 24  # assumption: one boat fills in about fifteen minutes at best
MEN_ALLOWED_SIDE = "starboard"  # assumption: port men only as crew, per Lightoller's reported policy
WATER_RESCUE_LIMIT = 40  # Wikipedia, Sinking of the Titanic: around 40 rescued from the water


def _row(boat, side, kind, x, hour, minute):
    seats = {"standard": STANDARD_SEATS, "cutter": CUTTER_SEATS, "collapsible": COLLAPSIBLE_SEATS}[kind]
    return dict(id=str(boat), side=side, kind=kind, seats=seats, x=x, launch_step=clock_step(hour, minute))


# Odd numbers starboard, even port. Station x is an assumption: forward group near the bridge, aft group aft.
BOAT_TABLE = [
    _row(7, "starboard", "standard", 26, 0, 40),
    _row(5, "starboard", "standard", 27, 0, 45),
    _row(3, "starboard", "standard", 28, 0, 55),
    _row(8, "port", "standard", 26, 1, 0),
    _row(1, "starboard", "cutter", 29, 1, 5),
    _row(6, "port", "standard", 27, 1, 10),
    _row(16, "port", "standard", 11, 1, 20),
    _row(14, "port", "standard", 12, 1, 25),
    _row(12, "port", "standard", 13, 1, 30),
    _row(9, "starboard", "standard", 14, 1, 30),
    _row(11, "starboard", "standard", 13, 1, 35),
    _row(13, "starboard", "standard", 12, 1, 40),
    _row(15, "starboard", "standard", 11, 1, 40),
    _row(2, "port", "cutter", 29, 1, 45),
    _row(10, "port", "standard", 14, 1, 50),
    _row(4, "port", "standard", 28, 1, 50),
    _row("C", "starboard", "collapsible", 30, 2, 0),
    _row("D", "port", "collapsible", 30, 2, 5),
]
FLOAT_OFF = [  # Wormstedt: A floated off upright and B upside down as the bridge went under.
    dict(id="A", side="starboard", kind="collapsible", seats=COLLAPSIBLE_SEATS, x=31, launch_step=BRIDGE_UNDER_STEP),
    dict(id="B", side="port", kind="collapsible", seats=COLLAPSIBLE_SEATS, x=31, launch_step=BRIDGE_UNDER_STEP),
]
TOTAL_SEATS = sum(row["seats"] for row in BOAT_TABLE + FLOAT_OFF)


class Lifeboat:
    def __init__(self, row, deck_row, allow_all_sides=False):
        self.id, self.side, self.kind = row["id"], row["side"], row["kind"]
        self.seats, self.launch_step = row["seats"], row["launch_step"]
        self.station = (row["x"], deck_row)
        self.allow_all_sides = allow_all_sides
        self.aboard = []
        self.crew_aboard = 0
        self.state = "stowed"  # stowed, loading, lowered, floated

    @property
    def free_seats(self):
        return self.seats - len(self.aboard)

    def eligible(self, agent):
        """Boarding order is the ship's rule, applied equally to every mind."""
        if agent.group in ("woman", "child") or self.allow_all_sides:
            return True
        return self.side == MEN_ALLOWED_SIDE

    def export_dict(self):
        return dict(id=self.id, side=self.side, kind=self.kind, seats=self.seats, launch_step=self.launch_step, aboard=len(self.aboard), state=self.state)


class LifeboatSchedule:
    def __init__(self, world, crew_seats=CREW_SEATS, allow_all_sides=False, boarding_rule=True):
        self.boarding_rule = boarding_rule
        deck_row = world.assembly_points[0][1]
        self.crew_seats = crew_seats
        self.allow_all_sides = allow_all_sides
        self.boats = [Lifeboat(row, deck_row, allow_all_sides=allow_all_sides) for row in BOAT_TABLE]
        self.floating = [Lifeboat(row, deck_row, allow_all_sides=allow_all_sides) for row in FLOAT_OFF]
        self.water_rescued = 0

    def open_stations(self, t):
        """Stations with a boat still on the davits; people walk there even before loading starts."""
        return sorted({boat.station for boat in self.boats if boat.state != "lowered"})

    def boats_at(self, station):
        return [boat for boat in self.boats if boat.station == station and boat.state != "lowered"]

    def load(self, t, at_station):
        """Board waiting people. Returns [(agent, boat)] in boarding order."""
        boarded = []
        if t < LOAD_STEP:
            return boarded
        for boat in self.boats:
            if boat.state == "lowered":
                continue
            boat.state = "loading"
            waiting = at_station.get(boat.station, [])
            organisers = [a for a in waiting if a.role in ("officer", "evac_worker")]
            passengers = [a for a in waiting if a.role not in ("officer", "evac_worker", "captain")]
            limit = min(MAX_LOAD_PER_STEP, BASE_LOAD_PER_STEP + LOAD_PER_ORGANISER * len(organisers))
            if self.boarding_rule:
                order = sorted((a for a in passengers if boat.eligible(a)),
                               key=lambda a: (a.group == "man", a.id))
            else:  # assumption: fixed scrambled order, because id order would favour first class
                order = sorted((a for a in passengers if boat.eligible(a)),
                               key=lambda a: (a.id * 2654435761 % 4294967296))
                order = sorted(passengers, key=lambda a: a.id * 2654435761 % 4294967296)
=======
            order = sorted((a for a in passengers if boat.eligible(a)), key=lambda a: (a.group == "man", a.id))
>>>>>>> a8750dbb13c6822b142844cb867d976177092ef4
            # Rowers board only as the boat is about to leave, so organisers keep working.
            if t >= boat.launch_step - 1:
                seats_left = self.crew_seats - boat.crew_aboard
                order = sorted(organisers, key=lambda a: a.id)[: max(0, seats_left)] + order
            for agent in order:
                if limit <= 0 or boat.free_seats <= 0:
                    break
                if agent.status != "aboard":
                    continue
                boat.aboard.append(agent.id)
                boat.crew_aboard += agent.role in ("officer", "evac_worker")
                agent.board(boat)
                boarded.append((agent, boat))
                limit -= 1
        return boarded

    def launch_due(self, t):
        """Boats leaving this step, in launch order."""
        due = [boat for boat in self.boats if boat.state != "lowered" and boat.launch_step <= t]
        for boat in due:
            boat.state = "lowered"
        return due

    def float_off_due(self, t):
        due = [boat for boat in self.floating if boat.state == "stowed" and boat.launch_step <= t]
        for boat in due:
            boat.state = "floated"
        return due

    def rescue(self, agent):
        """Pull one person from the water onto a floated collapsible, if a place remains."""
        if self.water_rescued >= WATER_RESCUE_LIMIT:
            return None
        for boat in self.floating:
            if boat.state == "floated" and boat.free_seats > 0:
                boat.aboard.append(agent.id)
                self.water_rescued += 1
                agent.board(boat)
                return boat
        return None

    def export_dict(self):
        return [boat.export_dict() for boat in self.boats + self.floating]
