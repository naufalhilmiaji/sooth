"""Pure-function checks. No network, no SDK needed.

Run: python3 tests/test_core.py   (or: pytest)
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # direct-run without install

import sooth
import sooth.cli
from sooth.claims import split_claims, split_segments
from sooth.report import (
    bar,
    exit_code,
    log_record,
    render_json,
    render_markdown,
    verdicts_from_record,
)
from sooth.verify import (
    FAIL,
    PASS,
    REVIEW,
    UNCHECKABLE,
    Verdict,
    VerifyResult,
    apply_safeguards,
    attach_evidence,
    build_questions,
    build_state,
    evidence_candidates,
    map_verdict,
    missing_numbers,
)


def v(kind: str, **kw) -> Verdict:
    base = {"claim_id": "c1", "claim_text": "Refunds take 3 days.", "line": 1, "kind": kind}
    base.update(kw)
    return Verdict(**base)


# --- claims.split_claims ---


def test_split_keeps_decimals_and_counts_lines():
    text = "# Title\nRefunds take 3.5 days.\n\nWe support Bitcoin payments here.\n"
    claims = split_claims(text)
    assert [c.text for c in claims] == [
        "Refunds take 3.5 days.",
        "We support Bitcoin payments here.",
    ]
    assert claims[0].line == 2 and claims[1].line == 4
    assert claims[0].id == "c1" and claims[1].id == "c2"


def test_split_skips_headings_questions_fragments():
    text = "## Section\nDo you like it?\nYes\nGreat product overall for teams.\n- Bullet claim about billing refunds.\n"
    claims = split_claims(text)
    assert [c.text for c in claims] == [
        "Great product overall for teams.",
        "Bullet claim about billing refunds.",
    ]


def test_split_multiple_sentences_one_line():
    claims = split_claims("We accept card payments only. Bank transfers also work fine here. Short.")
    assert [c.text for c in claims] == [
        "We accept card payments only.",
        "Bank transfers also work fine here.",
    ]


def test_split_bold_handling():
    text = (
        "**Aturan Berlaku Umum (Bukan Hanya Grup Bakrie)**\n"
        "1. **Tingkat Risiko Saham Kembali ke Gocap**\n"
        "**JGLE (~Rp 69):** Hanya butuh turun ~27,5% ke Rp 50.\n"
        "Batas **Rp 50 menjadi Rp 1** per saham berlaku segera.\n"
    )
    claims = split_claims(text)
    assert [c.text for c in claims] == [
        "JGLE (~Rp 69): Hanya butuh turun ~27,5% ke Rp 50.",
        "Batas Rp 50 menjadi Rp 1 per saham berlaku segera.",
    ]


# --- verify.map_verdict ---


def test_verdict_uncheckable_below_floor():
    z = map_verdict(split_claims("Vague praise for the team.")[0], 0.2, "not_found", {}, 0.9, 0.7)
    assert z.kind == UNCHECKABLE


def test_verdict_review_below_threshold():
    z = map_verdict(
        split_claims("Vague praise for the team.")[0],
        0.9,
        "supports",
        {"supports": 0.5, "contradicts": 0.3, "not_found": 0.2},
        0.55,
        0.7,
    )
    assert z.kind == REVIEW


def test_verdict_pass_fail_notfound():
    c = split_claims("Vague praise for the team.")[0]
    assert map_verdict(c, 1.0, "supports", {"supports": 0.9}, 0.9, 0.7).kind == PASS
    assert map_verdict(c, 1.0, "contradicts", {"contradicts": 0.9}, 0.9, 0.7).kind == FAIL
    assert map_verdict(c, 1.0, "not_found", {"not_found": 0.9}, 0.9, 0.7).kind == REVIEW


def test_verdict_threshold_boundary_inclusive():
    c = split_claims("Vague praise for the team.")[0]
    assert map_verdict(c, 1.0, "supports", {}, 0.7, 0.7).kind == PASS


# --- verify builders ---


def test_builders_two_questions_per_claim():
    claims = split_claims("A concrete claim about billing.\nAnother concrete claim about refunds.")
    segs = split_segments("Refunds take three days.", "a.md")
    cands = {c.id: segs for c in claims}
    q = build_questions(claims, cands)
    assert set(q) == {
        "c1_checkable",
        "c1_verdict",
        "c1_details",
        "c1_evidence",
        "c2_checkable",
        "c2_verdict",
        "c2_details",
        "c2_evidence",
    }
    assert q["c1_checkable"]["type"] == "noul" and q["c1_verdict"]["type"] == "choice"
    assert "none" in q["c1_evidence"]["criteria"]
    state = build_state(claims, [("a.md", "text")], segs)
    assert state["sources"][0] == {"name": "a.md", "text": "text"}
    assert state["claims"][0]["text"] == claims[0].text
    assert state["segments"][0]["id"] == segs[0].id


def test_split_segments_ids_and_sources():
    segs = split_segments("First sentence here now.\nSecond sentence here now.", "x.md")
    assert [(s.id, s.source, s.line) for s in segs] == [("s1", "x.md", 1), ("s2", "x.md", 2)]
    more = split_segments("Third sentence here now.", "y.md", start_index=len(segs) + 1)
    assert more[0].id == "s3"


def test_evidence_candidates_prefer_number_match():
    segs = [
        split_segments("The sky is very blue today indeed.", "a.md")[0],
        split_segments("BNBR rights issue was priced at Rp 53.", "a.md", 2)[0],
        split_segments("Unrelated gardening tips for beginners.", "a.md", 3)[0],
    ]
    top = evidence_candidates("Rights issue BNBR at Rp 53 completed.", segs)
    assert top[0].id == "s2"


def test_evidence_candidates_word_overlap():
    segs = [
        split_segments("Stocks moved little in quiet trading this week overall.", "a.md")[0],
        split_segments("Refund requests must reach support within thirty days.", "a.md", 2)[0],
    ]
    top = evidence_candidates("Refund requests within thirty days qualify for money back.", segs)
    assert top[0].id == "s2"


def test_attach_evidence():
    c = split_claims("Vague praise for the team.")[0]
    base = map_verdict(c, 1.0, "supports", {}, 0.9, 0.7)
    seg = split_segments("Team delivered the project on time.", "a.md")[0]
    v = attach_evidence(base, {seg.id: seg}, seg.id)
    assert v.evidence_text == seg.text and v.evidence_line == 1 and v.evidence_source == "a.md"
    assert attach_evidence(base, {seg.id: seg}, "none").evidence_text is None


def test_missing_numbers_flags_smuggled_values():
    sources = ["Rights issue at Rp 53. Drop about 74% to reach 50. Stock at Rp 69."]
    assert missing_numbers("BNBR rights issue at Rp 53.", sources) == []
    assert missing_numbers("DEWA is priced at about Rp 110 today.", sources) == ["110"]
    # decimal commas and dots normalize: 27,5 matches 27,5; 5.000 matches 5000
    assert missing_numbers("Fell 27,5% from Rp 5.000.", ["Down 27,5% from Rp 5000."]) == []


def test_apply_safeguards_demotes_pass():
    c = split_claims("Vague praise for the team.")[0]
    base = map_verdict(c, 1.0, "supports", {"supports": 0.9}, 0.9, 0.7)
    assert apply_safeguards(base, 0.9, []).kind == PASS
    assert apply_safeguards(base, 0.3, []).kind == REVIEW
    assert apply_safeguards(base, 0.9, ["110"]).kind == REVIEW
    fail = map_verdict(c, 1.0, "contradicts", {"contradicts": 0.9}, 0.9, 0.7)
    assert apply_safeguards(fail, 0.1, ["99"]).kind == FAIL  # FAIL stays FAIL


# --- report ---


def test_bar_length_proportional():
    assert bar(0.0) == "░" * 8 and bar(1.0) == "█" * 8 and len(bar(0.5)) == 8


def test_render_all_claims_once_and_counts():
    verdicts = [
        v(PASS, confidence=0.9, probabilities={"supports": 0.9}),
        v(FAIL, claim_id="c2", confidence=0.87, probabilities={"contradicts": 0.87}),
        v(REVIEW, claim_id="c3", confidence=0.54, probabilities={"not_found": 0.54}),
    ]
    out = render_markdown(verdicts, 0.7)
    assert "PASS 1 · FAIL 1 · REVIEW 1 · UNCHECKABLE 0" in out
    assert out.count("| 1 |") == 1 and out.count("| 2 |") == 1 and out.count("| 3 |") == 1
    assert "## Needs review" in out and "line 1" in out


def test_exit_codes():
    assert exit_code([v(PASS), v(UNCHECKABLE)]) == 0
    assert exit_code([v(REVIEW)]) == 2
    assert exit_code([v(PASS), v(REVIEW), v(FAIL)]) == 1


def test_log_record_roundtrip_no_secret():
    result = VerifyResult(
        verdicts=[v(PASS, confidence=0.9, probabilities={"supports": 0.9})],
        model="jev-1.13.0",
        usage={"input_tokens": 10, "output_tokens": 1},
    )
    rec = log_record(result, 0.7, ["a.md"], "draft.md")
    parsed = json.loads(json.dumps(rec))
    assert parsed["model"] == "jev-1.13.0" and parsed["results"][0]["kind"] == PASS
    assert "api_key" not in json.dumps(parsed).lower()


def test_verdicts_from_record_roundtrip():
    """log_record → JSON → verdicts_from_record is lossless (demo replay path)."""
    result = VerifyResult(
        verdicts=[
            v(PASS, confidence=0.9, probabilities={"supports": 0.9}, details_p=0.9,
              evidence_id="s1", evidence_text="Source line.", evidence_line=3,
              evidence_source="a.md"),
            v(FAIL, claim_id="c2", confidence=1.0, probabilities={"contradicts": 1.0},
              missing_numbers=("33",)),
        ],
        model="jev-1.13.0",
        usage={"input_tokens": 10, "output_tokens": 1},
    )
    back = verdicts_from_record(json.loads(json.dumps(log_record(result, 0.7, ["a.md"], "d.md"))))
    assert [(x.claim_id, x.kind, x.confidence) for x in back] == [("c1", PASS, 0.9), ("c2", FAIL, 1.0)]
    assert back[0].evidence_text == "Source line." and back[0].evidence_line == 3
    assert back[1].missing_numbers == ("33",) and back[1].evidence_text is None


# --- report.render_json ---


def test_render_json_shape_and_agreement_with_exit_code():
    verdicts = [
        v(PASS, confidence=0.98, probabilities={"supports": 0.98}, details_p=0.9),
        v(FAIL, claim_id="c2", confidence=1.0, probabilities={"contradicts": 1.0},
          missing_numbers=("2,000",), evidence_id="s1", evidence_text="limit is 500 req/s.",
          evidence_line=11, evidence_source="notes.md"),
        v(UNCHECKABLE, claim_id="c3", p_checkable=0.16),
    ]
    payload = json.loads(render_json(verdicts, 0.7))
    assert payload["summary"] == {
        "pass": 1, "fail": 1, "review": 0, "uncheckable": 1, "threshold": 0.7,
    }
    assert payload["exit_code"] == exit_code(verdicts) == 1
    assert [d["kind"] for d in payload["verdicts"]] == [PASS, FAIL, UNCHECKABLE]
    assert payload["verdicts"][1]["missing_numbers"] == ["2,000"]
    assert payload["verdicts"][1]["evidence"]["line"] == 11
    assert payload["verdicts"][2]["evidence"] is None
    assert "api_key" not in json.dumps(payload).lower()


def test_render_json_agrees_with_log_record_verdicts():
    """The two JSON surfaces must not drift apart."""
    result = VerifyResult(verdicts=[v(PASS, confidence=0.9)], model="m", usage={})
    rec = log_record(result, 0.7, ["a.md"], "d.md")
    payload = json.loads(render_json(result.verdicts, 0.7))
    assert rec["results"] == payload["verdicts"]


# --- packaging / CLI surface ---


def test_version_comes_from_packaging_metadata():
    """Guard the drift bug: __version__ must never be a stale hardcoded literal."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert sooth.__version__ in (declared, "0.0.0+unknown"), (
        f"__version__ is {sooth.__version__!r} but pyproject declares {declared!r}"
    )
    assert declared.count(".") == 2 and all(part.isdigit() for part in declared.split("."))


def test_demo_fixtures_are_valid_records():
    """Every bundled --case must replay: valid JSON, real fields, unambiguous verdicts."""
    for case, (filename, _blurb) in sooth.cli.DEMO_CASES.items():
        path = Path(__file__).resolve().parents[1] / "src" / "sooth" / filename
        assert path.is_file(), f"demo case {case!r} points at missing {filename}"
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["results"], f"{case}: empty results"
        assert 0.0 < record["threshold"] < 1.0
        assert record["model"].startswith("jev-")
        for r in record["results"]:
            assert r["kind"] in {PASS, FAIL, REVIEW, UNCHECKABLE}
            assert r["text"].strip()
        verdicts = verdicts_from_record(record)
        assert len(verdicts) == len(record["results"])


def test_cli_demo_replays_offline():
    """`sooth demo` on every case: no network, report on stdout, exit code from the record."""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    for case in sooth.cli.DEMO_CASES:
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = sooth.cli.main(["demo", "--case", case])
        out = buf.getvalue()
        assert "PASS" in out and "| # | Claim | Verdict |" in out
        assert code in (0, 1, 2), f"{case}: unexpected exit {code}"
        assert "error" not in err.getvalue().lower()


def test_cli_demo_json_is_machine_readable():
    import io
    from contextlib import redirect_stderr, redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(io.StringIO()):
        code = sooth.cli.main(["demo", "--format", "json"])
    payload = json.loads(buf.getvalue())
    assert payload["exit_code"] == code
    assert sum(payload["summary"][k] for k in ("pass", "fail", "review", "uncheckable")) \
        == len(payload["verdicts"])


def test_cli_usage_errors_exit_3():
    import io
    from contextlib import redirect_stderr, redirect_stdout

    for argv in ([], ["--source", "a.md"], ["--text", "b.md"]):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert sooth.cli.main(argv) == 3


def test_cli_version_flag():
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            sooth.cli.parse_args(["--version"])
    except SystemExit as e:
        assert e.code == 0
    else:  # pragma: no cover - argparse always exits on --version
        raise AssertionError("--version did not exit")
    assert buf.getvalue().strip() == f"sooth {sooth.__version__}"


def test_cli_format_choices_are_wired():
    assert set(sooth.cli.RENDERERS) == {"md", "plain", "json"}
    assert sooth.cli.DEFAULT_CASE in sooth.cli.DEMO_CASES


if __name__ == "__main__":
    fns = [f for name, f in sorted(globals().items()) if name.startswith("test_") and callable(f)]
    for fn in fns:
        fn()
    print(f"ok — {len(fns)} checks passed")
