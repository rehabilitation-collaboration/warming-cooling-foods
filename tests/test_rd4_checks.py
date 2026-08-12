"""Behaviour tests for RD-4's two post-completion invariants.

Both detectors exist because the failures they look for are only visible once
every coding is in, and both were written to run without `claims.csv` — a
completeness check measured against the known set is what the Route D goal
declaration lists first among its failure conditions.
"""

import pandas as pd

from src import rd4_checks as rc


def _cand(rows):
    return pd.DataFrame(rows, columns=["source_id", "candidate", "lines", "paths"])


def _inc(rows):
    return pd.DataFrame(rows, columns=["source_id", "candidate", "direction"])


class TestHeadNounConflicts:
    def test_flags_a_bare_token_between_two_opposite_modified_forms(self):
        """D61's case: 果物 is the residue of 寒冷地の果物 and 南国の果物."""
        cand = _cand([
            ("s1", "果物", "10;20", "prose"),
            ("s1", "寒冷地の果物", "10", "list"),
            ("s1", "南国の果物", "20", "list"),
        ])
        inc = _inc([("s1", "果物", "warm"), ("s1", "寒冷地の果物", "warm"),
                    ("s1", "南国の果物", "cool")])
        out = rc.head_noun_conflicts(inc, cand)
        assert len(out) == 1
        assert out.iloc[0]["head_noun"] == "果物"

    def test_a_list_line_naming_a_warm_and_a_cool_food_is_not_a_conflict(self):
        """The ordinary case the loose version of this check drowned in."""
        cand = _cand([("s1", "にんにく", "10", "list"), ("s1", "大根", "10", "list")])
        inc = _inc([("s1", "にんにく", "warm"), ("s1", "大根", "cool")])
        assert rc.head_noun_conflicts(inc, cand).empty

    def test_modified_forms_that_agree_are_not_a_conflict(self):
        cand = _cand([
            ("s1", "果物", "10;20", "prose"),
            ("s1", "寒冷地の果物", "10", "list"),
            ("s1", "冬の果物", "20", "list"),
        ])
        inc = _inc([("s1", "果物", "warm"), ("s1", "寒冷地の果物", "warm"),
                    ("s1", "冬の果物", "warm")])
        assert rc.head_noun_conflicts(inc, cand).empty

    def test_forms_on_unrelated_lines_are_not_a_conflict(self):
        """Sharing a substring is not enough — they have to share an emission line."""
        cand = _cand([
            ("s1", "果物", "10", "prose"),
            ("s1", "寒冷地の果物", "50", "list"),
            ("s1", "南国の果物", "60", "list"),
        ])
        inc = _inc([("s1", "果物", "warm"), ("s1", "寒冷地の果物", "warm"),
                    ("s1", "南国の果物", "cool")])
        assert rc.head_noun_conflicts(inc, cand).empty


class TestNonVerbatim:
    def test_a_span_the_source_does_not_contain_is_reported(self, tmp_path, monkeypatch):
        """D58's paren expansion can leave a span that is not contiguous."""
        monkeypatch.setattr(rc, "SOURCES_RAW_DIR", tmp_path)
        (tmp_path / "s1.txt").write_text("酒粕＋鮭（温性）＋にんじん", encoding="utf-8")
        out = rc.non_verbatim(_cand([("s1", "酒粕＋鮭＋にんじん", "1", "list")]))
        assert len(out) == 1

    def test_a_wrapped_splice_is_not_reported(self, tmp_path, monkeypatch):
        """The wrapped path joins two lines on purpose; that is not this defect."""
        monkeypatch.setattr(rc, "SOURCES_RAW_DIR", tmp_path)
        (tmp_path / "s1.txt").write_text("かき氷\nサラダ", encoding="utf-8")
        out = rc.non_verbatim(_cand([("s1", "かき氷サラダ", "1", "wrapped")]))
        assert out.empty

    def test_a_verbatim_span_is_not_reported(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rc, "SOURCES_RAW_DIR", tmp_path)
        (tmp_path / "s1.txt").write_text("体を温める食材は生姜です", encoding="utf-8")
        assert rc.non_verbatim(_cand([("s1", "生姜", "1", "prose")])).empty
