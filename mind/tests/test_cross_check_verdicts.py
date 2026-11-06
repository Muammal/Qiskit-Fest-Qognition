"""library_cross_check verdicts are computed, so a mismatch shows as FAIL."""
import mind.experiments.validate as validate


def verdicts():
    return {name.split(" (")[0]: result for name, result in validate.library_cross_check().items()}


def test_huang_entropy_is_reported_as_a_failure():
    result = verdicts()["Huang QLBN Belief Entropy"]
    assert result.startswith("FAIL")
    assert "-0.4855" in result and "-0.9420" in result and "1.94" in result


def test_the_other_checks_pass_on_their_criteria():
    found = verdicts()
    for name in ("Wang-Busemeyer QQ Equality", "2D Luders Representability", "Busemeyer 2-Qubit Hamiltonian"):
        assert found[name].startswith("PASS"), found[name]


def test_a_broken_implementation_turns_the_verdict_to_fail(monkeypatch):
    monkeypatch.setattr(validate, "wang_busemeyer_qq_gap", lambda *_: (0.01, 0.1))
    monkeypatch.setattr(validate, "verify_2d_representability", lambda *_: True)
    found = verdicts()
    assert found["Wang-Busemeyer QQ Equality"].startswith("FAIL")
    assert found["2D Luders Representability"].startswith("FAIL")


def test_a_matching_huang_value_would_pass(monkeypatch):
    monkeypatch.setattr(validate, "belief_degree_huang", lambda *_: validate.HUANG_PUBLISHED_DB)
    assert verdicts()["Huang QLBN Belief Entropy"].startswith("PASS")
