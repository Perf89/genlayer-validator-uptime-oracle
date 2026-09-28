"""
Offline tests for the strict result validation in validator_uptime_oracle.py.

These run in plain Python (no GenLayer runtime needed): they load only the
pure helper functions (_validate_result, _parse_llm_json) from the contract
source, so they always test the exact code that is deployed.

    python3 tests/test_result_validation.py
"""
import json
import pathlib
import typing

SRC = (pathlib.Path(__file__).parent.parent / "validator_uptime_oracle.py").read_text()
start = SRC.index("MAX_BPS = 10000")
end = SRC.index("@allow_storage")
ns = {"json": json, "typing": typing}
exec(SRC[start:end], ns)
validate, parse = ns["_validate_result"], ns["_parse_llm_json"]


def rejects(case):
    try:
        validate(case)
    except ValueError:
        return True
    return False


def test_accepts_well_formed():
    out = validate({"claim_supported": True, "measured_uptime_bps": 9990, "reasoning": "ok"})
    assert out == {"claim_supported": True, "measured_uptime_bps": 9990, "reasoning": "ok"}


def test_boundaries_accepted():
    assert validate({"claim_supported": False, "measured_uptime_bps": 0, "reasoning": ""})
    assert validate({"claim_supported": True, "measured_uptime_bps": 10000, "reasoning": ""})


def test_claim_supported_must_be_real_boolean():
    for bad in ("false", "true", "False", 0, 1, None):
        assert rejects({"claim_supported": bad, "measured_uptime_bps": 0, "reasoning": "x"}), bad


def test_uptime_must_be_int_in_range():
    for bad in (True, False, 99.9, "9990", None, -1, 10001):
        assert rejects({"claim_supported": True, "measured_uptime_bps": bad, "reasoning": "x"}), bad


def test_reasoning_must_be_string():
    for bad in (5, None, ["a"], {"a": 1}):
        assert rejects({"claim_supported": True, "measured_uptime_bps": 1, "reasoning": bad}), bad


def test_missing_fields_and_wrong_container():
    assert rejects({"measured_uptime_bps": 1, "reasoning": "x"})
    assert rejects({"claim_supported": True, "reasoning": "x"})
    assert rejects({"claim_supported": True, "measured_uptime_bps": 1})
    assert rejects([1, 2, 3])
    assert rejects("not a dict")


def test_reasoning_is_truncated():
    out = validate({"claim_supported": True, "measured_uptime_bps": 1, "reasoning": "x" * 900})
    assert len(out["reasoning"]) == 500


def test_parse_tolerates_code_fences():
    assert parse('{"a": 1}') == {"a": 1}
    assert parse('```json\n{"a": 1}\n```') == {"a": 1}


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(f"{len(tests)} tests passed")
