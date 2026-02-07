"""
Tests Fase 4 Plan Redis L2: Canonical query normalization.
- Mismas queries con distinto orden en arrays ⇒ mismo hash/key.
- Params equivalentes (incl. defaults) ⇒ mismo key.
"""
import pytest
from app.core.cache_keys import canonicalize_markets_query, build_markets_cache_key


class TestCanonicalizeMarketsQuery:
    """canonicalize_markets_query produce string determinístico."""

    def test_defaults_applied(self):
        # Sin params → mismo que explícito con defaults
        empty = canonicalize_markets_query({})
        explicit = canonicalize_markets_query({
            "limit": 50,
            "offset": 0,
            "order": "createdAt",
            "ascending": False,
            "closed": "false",
        })
        assert empty == explicit

    def test_same_key_different_array_order(self):
        # id[] en distinto orden → mismo canonical
        p1 = {"id": ["b", "a", "c"], "limit": 10}
        p2 = {"id": ["c", "a", "b"], "limit": 10}
        c1 = canonicalize_markets_query(p1)
        c2 = canonicalize_markets_query(p2)
        assert c1 == c2
        assert "a,b,c" in c1 or "id=a,b,c" in c1

    def test_same_key_array_deduped(self):
        p1 = {"slug": ["x", "x", "y"], "limit": 25}
        p2 = {"slug": ["y", "x"], "limit": 25}
        assert canonicalize_markets_query(p1) == canonicalize_markets_query(p2)

    def test_boolean_normalized(self):
        c_false = canonicalize_markets_query({"ascending": False})
        c_true = canonicalize_markets_query({"ascending": True})
        assert "false" in c_false
        assert "true" in c_true
        assert c_false != c_true

    def test_tag_id_included_when_present(self):
        c0 = canonicalize_markets_query({})
        c1 = canonicalize_markets_query({"tag_id": " politics"})
        assert "tag_id" not in c0
        assert "tag_id" in c1 and "politics" in c1
        assert c0 != c1

    def test_search_included_when_present(self):
        c1 = canonicalize_markets_query({"search": "foo"})
        assert "search=foo" in c1


class TestBuildMarketsCacheKey:
    """build_markets_cache_key: mismo canonical ⇒ misma key."""

    def test_deterministic_same_params(self):
        params = {"limit": 25, "offset": 0, "closed": "false", "order": "createdAt", "ascending": False}
        k1 = build_markets_cache_key(params)
        k2 = build_markets_cache_key(params)
        assert k1 == k2
        assert k1.startswith("gamma:markets:q:")
        assert len(k1) == len("gamma:markets:q:") + 64  # sha256 hex

    def test_different_params_different_key(self):
        k1 = build_markets_cache_key({"limit": 10, "offset": 0})
        k2 = build_markets_cache_key({"limit": 25, "offset": 0})
        assert k1 != k2

    def test_same_canonical_same_key_array_order(self):
        p1 = {"limit": 10, "id": ["a", "b", "c"]}
        p2 = {"limit": 10, "id": ["c", "b", "a"]}
        assert build_markets_cache_key(p1) == build_markets_cache_key(p2)

    def test_defaults_same_as_explicit(self):
        empty_key = build_markets_cache_key({})
        explicit_key = build_markets_cache_key({
            "limit": 50,
            "offset": 0,
            "order": "createdAt",
            "ascending": False,
            "closed": "false",
        })
        assert empty_key == explicit_key

    def test_key_prefix_optional(self):
        k0 = build_markets_cache_key({"limit": 1})
        kp = build_markets_cache_key({"limit": 1}, key_prefix="poly:")
        assert k0.startswith("gamma:markets:q:")
        assert kp.startswith("poly:gamma:markets:q:")
        assert k0 in kp or kp.endswith(k0)


# --- Fase 5: Buckets y TTL ---
from app.core.cache_keys import (
    BUCKET_BROAD,
    BUCKET_NARROW,
    BUCKET_SEARCH,
    get_markets_bucket,
    get_markets_soft_ttl_seconds,
    should_cache_markets_v1,
    SOFT_TTL_BROAD_SEC,
    SOFT_TTL_NARROW_SEC,
)


class TestMarketsBucketPhase5:
    """Bucket determinista: search, narrow, broad."""

    def test_search_bucket_when_search_param(self):
        assert get_markets_bucket({"search": "foo"}) == BUCKET_SEARCH
        assert get_markets_bucket({"limit": 25, "search": "x"}) == BUCKET_SEARCH
        # search solo espacios → vacío → broad
        assert get_markets_bucket({"search": "   "}) == BUCKET_BROAD

    def test_broad_bucket_no_search_no_arrays(self):
        assert get_markets_bucket({}) == BUCKET_BROAD
        assert get_markets_bucket({"tag_id": "politics", "limit": 50}) == BUCKET_BROAD

    def test_narrow_bucket_id_array_le_20(self):
        assert get_markets_bucket({"id": ["a", "b"]}) == BUCKET_NARROW
        assert get_markets_bucket({"id": list(str(i) for i in range(15))}) == BUCKET_NARROW

    def test_narrow_bucket_slug_array_le_20(self):
        assert get_markets_bucket({"slug": ["x", "y"]}) == BUCKET_NARROW

    def test_narrow_bucket_clob_array_le_20(self):
        assert get_markets_bucket({"clob_token_ids": ["t1"]}) == BUCKET_NARROW


class TestShouldCacheMarketsV1:
    """v1: no cachear cuando search está presente."""

    def test_no_cache_when_search(self):
        assert should_cache_markets_v1({"search": "q"}) is False

    def test_cache_when_no_search(self):
        assert should_cache_markets_v1({}) is True
        assert should_cache_markets_v1({"tag_id": "x"}) is True


class TestMarketsTTLPhase5:
    """TTL por bucket: broad 90s, narrow 300s."""

    def test_broad_ttl_90(self):
        assert get_markets_soft_ttl_seconds(BUCKET_BROAD) == SOFT_TTL_BROAD_SEC
        assert SOFT_TTL_BROAD_SEC == 90

    def test_narrow_ttl_300(self):
        assert get_markets_soft_ttl_seconds(BUCKET_NARROW) == SOFT_TTL_NARROW_SEC
        assert SOFT_TTL_NARROW_SEC == 300
