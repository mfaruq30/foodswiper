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
    out = gen.generate(VenueSummary("Via Carota", ["italian"], 3), "italian+ramen", "dine_in")
    assert out == "Hand-rolled pasta, just your speed"


def test_pregenerate_covers_every_pair() -> None:
    from app.reasons_llm import AnthropicReasonGenerator

    gen = AnthropicReasonGenerator(_FakeClient("a reason"))  # type: ignore[arg-type]
    venues = [VenueSummary("A", ["pizza"], 2), VenueSummary("B", ["sushi"], 3)]
    out = pregenerate(gen, venues, ["italian+ramen", "new"], "dine_in")
    assert len(out) == 4  # 2 venues x 2 archetypes
    assert out[("A", "new", "dine_in")] == "a reason"


def test_one_bad_venue_does_not_sink_the_batch() -> None:
    class _Flaky:
        def __init__(self) -> None:
            self.n = 0

        def generate(self, venue: VenueSummary, archetype: str, mode: str) -> str:
            self.n += 1
            if venue.name == "B":
                raise RuntimeError("model hiccup")
            return "ok"

    out = pregenerate(
        _Flaky(),
        [VenueSummary("A", ["pizza"], 2), VenueSummary("B", ["sushi"], 3)],
        ["new"],
        "dine_in",
    )
    assert ("A", "new", "dine_in") in out
    assert ("B", "new", "dine_in") not in out  # skipped, not fatal


def test_build_generator_is_none_without_key(monkeypatch: object) -> None:
    import os

    from app.reasons_llm import build_generator

    # No ANTHROPIC_API_KEY => None => templated fallback (the $0 demo, D-004).
    os.environ.pop("ANTHROPIC_API_KEY", None)
    assert build_generator() is None
