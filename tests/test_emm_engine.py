"""
The EMM engine must round-trip postings lists of any length, keep labels
apart, and derive deterministic tokens.
"""

from ers.schemes.common.emm_engine import EMMEngine


def test_long_postings_list_round_trips():
    engine = EMMEngine([4, 4], 2)
    key = engine.setup(16)
    values = [b"v%d" % i for i in range(3000)]
    db = engine.build_index(key, {b"label": values, b"other": [b"x"]})

    got = engine.resolve(key, engine.search(engine.trapdoor(key, b"label"), db))
    assert got == set(values)
    assert engine.resolve(key, engine.search(engine.trapdoor(key, b"other"), db)) == {b"x"}
    assert engine.search(engine.trapdoor(key, b"absent"), db) == set()


def test_tokens_are_deterministic_and_label_specific():
    engine = EMMEngine([4], 1)
    key = engine.setup(16)
    assert engine.trapdoor(key, b"a") == engine.trapdoor(key, b"a")
    assert engine.trapdoor(key, b"a") != engine.trapdoor(key, b"b")
    assert engine.trapdoor(engine.setup(16), b"a") != engine.trapdoor(key, b"a")
