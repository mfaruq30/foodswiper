"""LLM reason generation over a fake client — no key, no network, no cost."""

from app.reasons_llm import VenueSummary, pregenerate


class _FakeBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _FakeMessage:
        self.calls.append(kwargs)
        return _FakeMessage(self._text)


class _FakeClient:
    def __init__(self, text: str) -> None:
        self.messages = _FakeMessages(text)


def test_generator_trims_and_strips_quotes() -> None:
    from app.reasons_llm import AnthropicReasonGenerator

    gen = AnthropicReasonGenerator(_FakeClient('  "Hand-rolled pasta, just your speed"  '))  # type: ignore[arg-type]
    out = gen.generate(VenueSummary("v1", "Via Carota", ["italian"], 3), "italian+ramen", "dine_in")
    assert out == "Hand-rolled pasta, just your speed"


def test_overlong_reason_is_clamped_at_a_word_boundary() -> None:
    from app.reasons_llm import AnthropicReasonGenerator

    long_reason = (
        "This is a needlessly verbose recommendation that rambles well past "
        "the ninety character cap the card layout allows for a single line"
    )
    gen = AnthropicReasonGenerator(_FakeClient(long_reason))  # type: ignore[arg-type]
    out = gen.generate(VenueSummary("v1", "X", ["pizza"], 2), "new", "dine_in")
    assert len(out) <= 90
    assert not out.endswith(" ")  # clamped on a word boundary, no dangling space


def test_pregenerate_keys_by_id_not_name() -> None:
    from app.reasons_llm import AnthropicReasonGenerator

    gen = AnthropicReasonGenerator(_FakeClient("a reason"))  # type: ignore[arg-type]
    # Two DIFFERENT venues sharing the name "Joe's Pizza" — keying by name would
    # collapse them; keying by id keeps both (the bug the review caught).
    venues = [
        VenueSummary("osm:node:1", "Joe's Pizza", ["pizza"], 2),
        VenueSummary("osm:node:2", "Joe's Pizza", ["pizza"], 2),
    ]
    out = pregenerate(gen, venues, ["new"], "dine_in")
    assert len(out) == 2
    assert ("osm:node:1", "new", "dine_in") in out
    assert ("osm:node:2", "new", "dine_in") in out


def test_one_bad_venue_does_not_sink_the_batch() -> None:
    class _Flaky:
        def __init__(self) -> None:
            self.n = 0

        def generate(self, venue: VenueSummary, archetype: str, mode: str) -> str:
            self.n += 1
            if venue.id == "b":
                raise RuntimeError("model hiccup")
            return "ok"

    out = pregenerate(
        _Flaky(),
        [VenueSummary("a", "A", ["pizza"], 2), VenueSummary("b", "B", ["sushi"], 3)],
        ["new"],
        "dine_in",
    )
    assert ("a", "new", "dine_in") in out
    assert ("b", "new", "dine_in") not in out  # skipped, not fatal


def test_build_generator_is_none_without_key(monkeypatch: object) -> None:
    import os

    from app.reasons_llm import build_generator

    # No ANTHROPIC_API_KEY => None => templated fallback (the $0 demo, D-004).
    os.environ.pop("ANTHROPIC_API_KEY", None)
    assert build_generator() is None
