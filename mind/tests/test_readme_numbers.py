"""The README's scenario numbers come from a generated table, not from typing."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_readme_numbers", ROOT / "tools" / "make_readme_numbers.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

SAMPLE = dict(
    generated_utc="2026-11-06T00:00:00+00:00", commit="abc1234", seed=42,
    order_effect=dict(default_stress=0.3, lambda_0=0.3, lambda_1=0.04),
    volcano=dict(seeds=200, survival=dict(quantum=.995, classical_mixture=.995, classical=1.),
                 paired_delay_steps=dict(mean=.55, se=.091, later=45, earlier=5, same=90, n=140)),
    titanic=[dict(mapping="default", mind=m, total=2208, saved=600, dead=1608) for m in tool.MINDS],
    pompeii=[dict(mapping="B", mind=m, total=11500, dead=100) for m in tool.MINDS],
    waterloo=[dict(mapping="A", alarm=alarm, mind=m, total=100, off_site=90,
                   exposure={tool.AEGL2_OR_WORSE[0]: 3, tool.AEGL2_OR_WORSE[1]: 1, "below AEGL-1": 96})
              for m in tool.MINDS for alarm in (True, False)],
)


def test_render_uses_the_data_it_is_given():
    table = tool.render(SAMPLE)
    assert "abc1234" in table and "+0.55 steps" in table and "99.5%" in table
    assert "600 (27.2%)" in table and "| B | 100 | 100 | 100 |" in table and "| A | 4 | 4 | 4 |" in table


def test_readme_links_the_table_and_drops_the_stale_figures():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/results/SCENARIO_NUMBERS.md" in readme
    for stale in ("644–981", "287–679", "**849**", "**913+**", "15.6"):
        assert stale not in readme
