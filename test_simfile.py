"""Sim files come from strangers on the internet, so these tests are mostly about what is refused."""
import importlib.util
import json
from pathlib import Path

import contracts  # noqa: F401  (must load before mind)
import pygame
import pytest
from openpyxl import load_workbook

from engine.gui import IslandVisualizerApp
from main import open_builder
from stranded_physics.core.api import InterfaceError
from stranded_physics.entities import draft as edit
from stranded_physics.entities import simfile
from stranded_physics.entities.api import dump_scenario
from stranded_physics.runtime.game import build_game
from stranded_physics.runtime.report import report_sim

ROOT = Path(__file__).resolve().parent
MAP_CORNER = (286, 112)
spec = importlib.util.spec_from_file_location("publish_sim", ROOT / "tools" / "publish_sim.py")
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


def template(name="volcano_island"):
    return edit.template_draft(name)


def envelope(**changes):
    table = json.loads(simfile.to_bytes(template(), 7, "A", "B"))
    table.update(changes)
    return table


def as_bytes(table):
    return json.dumps(table).encode("utf-8")


def with_scenario(text):
    return as_bytes(envelope(scenario=text, sha256=simfile._digest(text)))


def scenario_text(draft):
    return dump_scenario(edit.to_scenario(draft))


# Templates --------------------------------------------------------------------

@pytest.mark.parametrize("name", [row[0] for row in edit.TEMPLATES])
def test_every_template_is_valid(name):
    assert edit.problem(template(name)) is None


@pytest.mark.parametrize("name, _title, _text, needs", edit.TEMPLATES)
def test_templates_say_truthfully_whether_they_need_the_data_pack(name, _title, _text, needs):
    assert simfile.needs_data_pack(edit.to_scenario(template(name))) is needs


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("name", ["volcano_island", "storm_island", "mind_contest"])
def test_playable_templates_build_on_several_islands(name, seed):
    game = build_game(edit.to_scenario(template(name)), seed)
    assert game.people


def test_shipped_cards_all_need_the_data_pack_except_as_declared():
    for path in edit.CARDS.glob("*.toml"):
        scenario = edit.to_scenario(edit.from_file(path))
        assert simfile.needs_data_pack(scenario) or {e.kind for e in scenario.entities} & simfile.SHIP_KINDS


@pytest.mark.parametrize("seed", [1, 2, 7, 42, 99])
@pytest.mark.parametrize("name", ["volcano_island", "storm_island", "mind_contest"])
def test_templates_start_people_and_shelters_on_land(name, seed):
    from stranded_physics.entities.api import EntitySpec
    from stranded_physics.entities.kinds import terrain_domain
    from stranded_physics.runtime.game import SEA, lonlat_to_map, terrain_picture

    draft = template(name)
    land = edit.terrain_entry(draft)
    domain = terrain_domain(EntitySpec("terrain", str(land["source"]), settings={k: land[k] for k in ("summit_m", "area_km2")}), seed)
    picture = terrain_picture(domain=domain, seed=seed)
    height, width = picture.shape[:2]
    for entry in draft.entries:
        where = edit.position(entry)
        if where and entry["kind"] in ("person", "group", "shelter"):
            fx, fy = lonlat_to_map(where)
            assert tuple(picture[int(fy * height), int(fx * width)]) != SEA, entry


def test_an_unplaced_person_gets_a_plain_message():
    from stranded_physics.builder_screen import BuilderScreen

    assert BuilderScreen._plain_problem("person: unknown settings [], missing settings ['start_lat', 'start_lon']") == "click the map to place the person."


# Round trip -------------------------------------------------------------------

def test_a_sim_survives_the_round_trip():
    draft = template()
    sim = simfile.read_sim(simfile.to_bytes(draft, 7, "Ada", "An eruption"))
    assert edit.to_scenario(sim.draft) == edit.to_scenario(draft)
    assert (sim.seed, sim.author, sim.description, sim.needs_data_pack) == (7, "Ada", "An eruption", False)


def test_same_file_and_seed_give_the_same_run():
    sim = simfile.read_sim(simfile.to_bytes(template(), 7))

    def run():
        game = build_game(edit.to_scenario(sim.draft), sim.seed)
        engine = game.simulation("quantum")
        engine.run()
        return [(s["event"], s["action"], s["pos_after"]) for s in engine.steps]

    assert run() == run()


def test_export_writes_a_file_named_after_the_id(tmp_path):
    path = simfile.export_sim(template(), 7, folder=tmp_path)
    assert path.name == "my_volcano_island.qsim" and simfile.read_path(path).seed == 7


def test_the_file_holds_nothing_from_this_computer():
    text = simfile.to_bytes(template(), 7).decode("utf-8")
    assert str(ROOT) not in text and "lenovo" not in text


# Refused ----------------------------------------------------------------------

@pytest.mark.parametrize("data, reason", [
    (b"\xff\xfe not text", "can't be read"),
    (b"[1, 2]", "isn't a Qognition"),
    (b'{"format": "other"}', "isn't a Qognition"),
    (b"[" * 200_000, "can't be read"),
    (b" " * (simfile.MAX_BYTES + 1), "too big"),
], ids=["not text", "a list", "another format", "deep nesting", "oversized"])
def test_junk_is_refused(data, reason):
    with pytest.raises(InterfaceError, match=reason):
        simfile.read_sim(data)


def test_a_newer_file_asks_for_an_update():
    with pytest.raises(InterfaceError, match="newer version"):
        simfile.read_sim(as_bytes(envelope(version=simfile.VERSION + 1)))


def test_extra_fields_are_refused():
    with pytest.raises(InterfaceError, match="missing or unknown"):
        simfile.read_sim(as_bytes(envelope(run="os.system('calc')")))


def test_a_changed_scenario_fails_the_hash():
    table = envelope()
    table["scenario"] = table["scenario"].replace("A villager", "Someone")
    with pytest.raises(InterfaceError, match="damaged"):
        simfile.read_sim(as_bytes(table))


@pytest.mark.parametrize("seed", [-1, 2 ** 40, "7", True, None])
def test_bad_seeds_are_refused(seed):
    with pytest.raises(InterfaceError, match="seed"):
        simfile.read_sim(as_bytes(envelope(seed=seed)))


@pytest.mark.parametrize("text", ["a\x00b", "a\u202eb", "a\x1b[2Jb", "x" * (simfile.MAX_SHORT_TEXT + 1)])
def test_unsafe_author_text_is_refused(text):
    with pytest.raises(InterfaceError):
        simfile.read_sim(as_bytes(envelope(author=text)))


def test_unsafe_text_inside_the_scenario_is_refused():
    text = scenario_text(template()).replace("A villager", "A\u202evillager")
    with pytest.raises(InterfaceError, match="can't be shown"):
        simfile.read_sim(with_scenario(text))


def test_a_shipped_id_is_refused_so_it_cant_borrow_results():
    text = scenario_text(template()).replace('"my_volcano_island"', '"st_vincent_2021"')
    with pytest.raises(InterfaceError, match="shipped"):
        simfile.read_sim(with_scenario(text))


def test_an_id_cant_become_a_path():
    text = scenario_text(template()).replace('"my_volcano_island"', '"../../evil"')
    with pytest.raises(InterfaceError, match="can't be used as an id"):
        simfile.read_sim(with_scenario(text))


def test_too_many_people_is_refused():
    draft = edit.Draft(template("mind_contest").header, tuple(
        {**entry, "count": 300} if entry["kind"] == "group" else entry for entry in template("mind_contest").entries))
    with pytest.raises(InterfaceError, match="people"):
        simfile.read_sim(with_scenario(scenario_text(draft)))


def test_too_long_a_run_is_refused():
    text = scenario_text(template()).replace("hours = 96", "hours = 100000")
    with pytest.raises(InterfaceError):
        simfile.read_sim(with_scenario(text))


@pytest.mark.parametrize("value", ["nan", "inf", "1e308"])
def test_impossible_numbers_are_refused(value):
    text = scenario_text(template()).replace("rain_mm_h = 1.0", f"rain_mm_h = {value}")
    assert value in text
    with pytest.raises(InterfaceError):
        simfile.read_sim(with_scenario(text))


def test_an_unknown_setting_is_refused():
    text = scenario_text(template()).replace("rain_mm_h = 1.0", 'rain_mm_h = 1.0\npath = "C:/Windows"')
    with pytest.raises(InterfaceError):
        simfile.read_sim(with_scenario(text))


def test_ships_cant_be_exported_yet():
    with pytest.raises(InterfaceError, match="Ship|ship"):
        simfile.to_bytes(edit.from_file(edit.CARDS / "titanic_1912.toml"), 1)


def test_only_qsim_files_open_from_a_path(tmp_path):
    other = tmp_path / "notes.txt"
    other.write_text("hello")
    with pytest.raises(InterfaceError, match="Only .qsim"):
        simfile.read_path(other)


# Links ------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["http://example.com/a.qsim", "file:///C:/Windows/win.ini", "ftp://example.com/a", "https://"])
def test_only_https_links_open(url):
    with pytest.raises(InterfaceError, match="https"):
        simfile._check_link(url)


def test_links_holding_a_password_are_refused():
    with pytest.raises(InterfaceError, match="password"):
        simfile._check_link("https://me:secret@example.com/a.qsim")


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"])
def test_links_to_local_addresses_are_refused(monkeypatch, address):
    family = 23 if ":" in address else 2
    monkeypatch.setattr(simfile.socket, "getaddrinfo", lambda *a, **k: [(family, 1, 6, "", (address, 443))])
    with pytest.raises(InterfaceError, match="public address"):
        simfile._check_link("https://looks-public.example/a.qsim")


def test_a_redirect_is_checked_too(monkeypatch):
    monkeypatch.setattr(simfile.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(InterfaceError):
        simfile._CheckedRedirects().redirect_request(None, None, 302, "", {}, "https://evil.example/x")


def test_github_file_pages_are_understood():
    assert simfile.normalise_link("https://github.com/a/b/blob/main/x.qsim ") == "https://raw.githubusercontent.com/a/b/main/x.qsim"


def test_gallery_rows_that_try_to_leave_the_folder_are_dropped():
    good = dict(file="good.qsim", title="Good", author="", description="", needs_data_pack=False, sha256="x")
    rows = [good, dict(good, file="../../evil.qsim"), dict(good, file="sub/evil.qsim"), dict(good, title="a\u202eb"), "junk", dict(title="no file")]
    data = json.dumps(dict(sims=rows)).encode()
    assert [row["file"] for row in simfile.parse_gallery(data)] == ["good.qsim"]


def test_a_gallery_sim_must_match_the_list(monkeypatch):
    monkeypatch.setattr(simfile, "_download", lambda url, limit: simfile.to_bytes(template(), 7))
    with pytest.raises(InterfaceError, match="doesn't match"):
        simfile.fetch_gallery_sim(dict(file="a.qsim", sha256="different"))


# The screen -------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    window = IslandVisualizerApp(seed=101, start_screen="event_choice", builder_factory=open_builder)
    window._open_builder()
    window.builder.save_folder, window.builder.sim_folder = tmp_path, tmp_path
    window.draw((0, 0))
    yield window
    pygame.quit()


def click(window, label):
    hot = next(h for h in window.builder.hot if h.label == label)
    window.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hot.rect.center), hot.rect.center)
    window.draw((0, 0))


def settle(window):
    if window.builder.net_thread is not None:
        window.builder.net_thread.join()
    window.draw((0, 0))


def test_the_builder_starts_by_asking_what_to_simulate(app):
    assert app.builder.start_open
    assert {h.label for h in app.builder.hot} >= {"template:volcano_island", "template:storm_island", "template:mind_contest"}


def test_one_click_gives_a_scenario_ready_to_play(app):
    click(app, "template:volcano_island")
    assert not app.builder.start_open and app.builder.problem is None


def test_guided_mode_hides_the_ship_kinds_and_technical_fields(app):
    click(app, "template:volcano_island")
    labels = {h.label for h in app.builder.hot}
    assert "add:person" in labels and "add:ship" not in labels and "field:id" not in labels and "field:start_utc" not in labels


def test_advanced_shows_them_again(app):
    click(app, "template:volcano_island")
    click(app, "Advanced")
    labels = {h.label for h in app.builder.hot}
    assert "add:ship" in labels and "field:id" in labels


def test_a_model_isnt_called_a_real_record(app):
    from stranded_physics.builder_screen import BuilderScreen

    assert BuilderScreen._source_text(dict(kind="ash", source="replay")) == "Built-in model"
    assert BuilderScreen._source_text(dict(kind="terrain", source="replay")) == "Real record"


def test_renaming_also_gives_a_usable_id(app):
    click(app, "template:volcano_island")
    builder = app.builder
    builder._apply(lambda: edit.set_title(builder.draft, "The Big One!"))
    assert builder.draft.header["id"] == "my_the_big_one"


def test_a_shipped_name_cant_take_a_shipped_id():
    assert edit.id_from_title("Con") not in edit.WINDOWS_DEVICE_NAMES and edit.usable_id(edit.id_from_title("???"))


def test_checklist_adds_what_is_missing_without_the_data_pack(app):
    click(app, "template:blank_island")
    click(app, "step:People")
    assert any(entry["kind"] == "person" for entry in app.builder.draft.entries)
    click(app, "step:Danger")
    kinds = {entry["kind"]: entry["source"] for entry in app.builder.draft.entries}
    assert kinds["eruption"] == "catalogue" and {"ash", "flow"} <= set(kinds)
    assert not simfile.needs_data_pack(edit.to_scenario(app.builder.draft))


def test_a_click_on_the_sea_is_refused(app):
    click(app, "template:blank_island")
    builder = app.builder
    builder._add("person")
    for _ in range(300):
        app.draw((0, 0))
        if builder.picture is not None:
            break
        pygame.time.wait(20)
    builder.click_pos = (MAP_CORNER[0] + 3, MAP_CORNER[1] + 3)
    builder._click_map()
    assert "sea" in builder.message and edit.position(builder.draft.entries[builder.selected]) is None


def test_undo_goes_back_a_step(app):
    click(app, "template:volcano_island")
    before = app.builder.draft
    click(app, "add:resource")
    assert app.builder.draft is not before
    click(app, "Undo")
    assert app.builder.draft is before


def test_ctrl_z_undoes(app):
    click(app, "template:volcano_island")
    before = app.builder.draft
    click(app, "add:resource")
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=pygame.KMOD_CTRL, unicode=""), (5, 5))
    assert app.builder.draft is before


def test_share_exports_a_file(app, tmp_path):
    click(app, "template:volcano_island")
    click(app, "Share")
    click(app, "Save .qsim file")
    assert (tmp_path / "my_volcano_island.qsim").exists()


def test_publish_needs_a_second_click_and_uploads_nothing_itself(app, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("stranded_physics.builder_screen.webbrowser.open", opened.append)
    click(app, "template:volcano_island")
    click(app, "Share")
    click(app, "Publish online")
    assert opened == [] and "public" in app.builder.message
    click(app, "Publish online")
    assert opened == [simfile.UPLOAD_PAGE] and (tmp_path / "my_volcano_island.qsim").exists()


def test_dropping_a_sim_on_the_window_opens_it(app, tmp_path):
    path = simfile.export_sim(template("storm_island"), 12, "Ada", folder=tmp_path)
    app.app_state = "event_choice"
    app.handle_event(pygame.event.Event(pygame.DROPFILE, file=str(path)), (5, 5))
    app.draw((0, 0))
    assert app.app_state == "builder" and app.builder.seed == 12
    assert app.builder.draft.header["id"] == "my_storm_island" and "Nobody has checked it" in app.builder.sim_note


def test_dropping_a_bad_file_says_why_and_changes_nothing(app, tmp_path):
    bad = tmp_path / "bad.qsim"
    bad.write_bytes(b"not a sim")
    before = app.builder.draft
    app.handle_event(pygame.event.Event(pygame.DROPFILE, file=str(bad)), (5, 5))
    assert app.builder.draft is before and app.builder.message_bad


def test_open_lists_exported_sims(app, tmp_path):
    simfile.export_sim(template(), 3, folder=tmp_path)
    app.builder.start_open = False
    app.draw((0, 0))
    click(app, "Open")
    click(app, "open:my_volcano_island")
    assert app.builder.seed == 3


def test_a_sim_that_needs_the_data_pack_explains_itself(app, monkeypatch):
    monkeypatch.setattr(simfile, "data_pack_present", lambda: False)
    app.builder.start_open = False
    app.builder.draft = template("st_vincent")
    app.draw((0, 0))
    app.builder._play()
    assert not app.builder.building and "fetch_artifacts" in app.builder.message


def test_community_rows_open_on_a_click(app, monkeypatch):
    row = dict(file="a.qsim", title="A sim", author="Ada", description="", needs_data_pack=False, sha256="x")
    monkeypatch.setattr(simfile, "fetch_gallery", lambda: [row])
    monkeypatch.setattr(simfile, "fetch_gallery_sim", lambda r: simfile.read_sim(simfile.to_bytes(template("storm_island"), 9)))
    click(app, "Open a file or community sim")
    click(app, "Community")
    settle(app)
    click(app, "community:a.qsim")
    settle(app)
    assert app.builder.seed == 9 and app.builder.draft.header["id"] == "my_storm_island"


def test_a_failed_download_is_shown_not_raised(app, monkeypatch):
    def fail():
        raise InterfaceError("Couldn't download that: no network")
    monkeypatch.setattr(simfile, "fetch_gallery", fail)
    click(app, "Open a file or community sim")
    click(app, "Community")
    settle(app)
    assert app.builder.message_bad and "no network" in app.builder.message


def test_the_builder_screen_text_fits_at_1080p(app):
    app.screen = pygame.display.set_mode((1920, 1080))
    click(app, "template:volcano_island")
    app.draw((0, 0))
    assert app.canvas.text_layer


# Headless and the gallery ------------------------------------------------------

def test_a_sim_file_runs_headless_and_writes_a_report(tmp_path):
    path = simfile.export_sim(template(), 4, "Ada", folder=tmp_path)
    workbook, folder = report_sim(str(path), out_dir=tmp_path / "reports")
    summary = {row[0].value: row[1].value for row in load_workbook(workbook)["Summary"].iter_rows(min_row=2)}
    assert summary["Made by"] == "Ada" and "Nobody" in summary["Checked by"]
    assert (folder / "timeline.csv").exists()


@pytest.fixture
def gallery(tmp_path, monkeypatch):
    for name, value in (("COMMUNITY", tmp_path), ("SIMS", tmp_path / "sims"), ("INDEX", tmp_path / "index.json"), ("PAGE", tmp_path / "README.md")):
        monkeypatch.setattr(publish, name, value)
    return tmp_path


def test_adding_a_sim_updates_the_list_and_the_page(gallery):
    source = simfile.export_sim(template(), 7, "Ada", "An eruption", gallery / "out")
    rows = publish.add(source)
    assert [row["file"] for row in rows] == ["my_volcano_island.qsim"]
    assert simfile.parse_gallery(publish.INDEX.read_bytes())[0]["title"] == "Eruption on a made-up island"
    assert "Ada" in publish.PAGE.read_text(encoding="utf-8") and publish.check() == []


def test_the_page_cant_be_broken_by_a_title():
    rows = [dict(file="a.qsim", title="x|y](http://evil)", author="<script>", description="a|b", needs_data_pack=False)]
    text = publish.page_text(rows)
    assert "<script>" not in text and "](http://evil)" not in text and "x/y" in text


def test_a_second_sim_cant_replace_a_published_one(gallery):
    publish.add(simfile.export_sim(template(), 7, folder=gallery / "out"))
    other = simfile.export_sim(template(), 8, folder=gallery / "out2")
    with pytest.raises(InterfaceError, match="already in the gallery"):
        publish.add(other)


def test_check_finds_a_bad_file_and_a_stale_list(gallery):
    publish.add(simfile.export_sim(template(), 7, folder=gallery / "out"))
    (publish.SIMS / "bad.qsim").write_bytes(b"nope")
    assert any("bad.qsim" in problem for problem in publish.check())
    (publish.SIMS / "bad.qsim").unlink()
    publish.INDEX.write_text("{}")
    assert any("out of date" in problem for problem in publish.check())


def test_the_published_gallery_is_valid():
    assert publish.check() == []
    assert len(publish.load_all()) >= 3
    assert not any(sim.needs_data_pack for _, sim in publish.load_all())
