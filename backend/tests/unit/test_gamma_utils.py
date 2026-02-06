"""
Unit tests for gamma_utils (parse_clob_token_ids).
"""
import pytest
from app.core.gamma_utils import parse_clob_token_ids


class TestParseClobTokenIds:
    """Tests for parse_clob_token_ids."""

    def test_none_returns_defaults(self):
        out = parse_clob_token_ids(None)
        assert out["primary_yes"] is None
        assert out["primary_no"] is None
        assert out["clob_token_ids_all"] is None
        assert out["clob_token_ids_by_key"] is None
        assert out["selection_hint"] == "none"
        assert out["primary"] is None

    def test_empty_string_returns_defaults(self):
        out = parse_clob_token_ids("")
        assert out["selection_hint"] == "none"

    def test_dict_yes_no_case_insensitive(self):
        out = parse_clob_token_ids({"YES": "tok_yes", "NO": "tok_no"})
        assert out["primary_yes"] == "tok_yes"
        assert out["primary_no"] == "tok_no"
        assert out["selection_hint"] == "primary_yes"
        assert out["primary"] == "tok_yes"
        assert out["clob_token_ids_by_key"] == {"YES": "tok_yes", "NO": "tok_no"}

    def test_dict_yes_no_lowercase(self):
        out = parse_clob_token_ids({"yes": "t1", "no": "t2"})
        assert out["primary_yes"] == "t1"
        assert out["primary_no"] == "t2"
        assert out["selection_hint"] == "primary_yes"
        assert out["primary"] == "t1"

    def test_dict_only_no(self):
        out = parse_clob_token_ids({"NO": "tok_no"})
        assert out["primary_yes"] is None
        assert out["primary_no"] == "tok_no"
        assert out["selection_hint"] == "primary_yes"
        assert out["primary"] == "tok_no"

    def test_list_no_semantics(self):
        out = parse_clob_token_ids(["t1", "t2"])
        assert out["primary_yes"] is None
        assert out["primary_no"] is None
        assert out["clob_token_ids_all"] == ["t1", "t2"]
        assert out["clob_token_ids_by_key"] is None
        assert out["selection_hint"] == "multi"
        assert out["primary"] == "t1"

    def test_list_single(self):
        out = parse_clob_token_ids(["t1"])
        assert out["selection_hint"] == "single"
        assert out["primary"] == "t1"
        assert out["clob_token_ids_all"] == ["t1"]

    def test_list_empty(self):
        out = parse_clob_token_ids([])
        assert out["selection_hint"] == "none"
        assert out["primary"] is None
        assert out["clob_token_ids_all"] == []

    def test_string_json_list(self):
        out = parse_clob_token_ids('["t1","t2"]')
        assert out["clob_token_ids_all"] == ["t1", "t2"]
        assert out["selection_hint"] == "multi"

    def test_string_json_dict(self):
        out = parse_clob_token_ids('{"YES":"y1","NO":"n1"}')
        assert out["primary_yes"] == "y1"
        assert out["primary_no"] == "n1"
        assert out["selection_hint"] == "primary_yes"

    def test_never_assume_list_0_is_yes(self):
        """List has no YES/NO semantics; primary_yes must stay None."""
        out = parse_clob_token_ids(["first_token_id", "second_token_id"])
        assert out["primary_yes"] is None
        assert out["primary_no"] is None
        assert out["clob_token_ids_all"] == ["first_token_id", "second_token_id"]
        assert out["selection_hint"] == "multi"
