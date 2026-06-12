"""Layer 5 reason generation with Claude Haiku (spec §7.6, D-004).

OFF THE SERVE PATH, ALWAYS. A deck request never calls this — it serves
templated reasons (app.reasons) and swaps in cached LLM text where present
(ReasonCache). This module runs in a BACKGROUND job that pre-generates reasons
into the cache, keyed by (restaurant, archetype, mode) so each pair is written
once and reused across users (app.archetype). Costs land on the offline job,
never on a user's latency.

Degraded mode (the $0 demo, spec §10.8): no ANTHROPIC_API_KEY => generation is
simply not run, the cache stays empty, every card keeps its templated reason.
Nothing here is on the critical path, so a missing key is a non-event.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import anthropic

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")

# The reason is a card subtitle — one short, specific line. Hard cap so a
# verbose model can't break the card layout; the templated fallback already
# guarantees a good line, so this is pure upside.
_MAX_TOKENS = 60

_SYSTEM = (
    "You write one-line restaurant recommendation reasons for a swipe app. "
    "Rules: ONE sentence, under 90 characters, specific and warm, no emoji, "
    "no quotes, no restaurant name (it's shown above the line). Speak to a "
    "diner whose taste is given. Never invent facts not provided."
)


@dataclass(slots=True)
class VenueSummary:
    """The minimal, non-identifying venue facts a reason may use."""

    name: str
    cuisines: list[str]
    price_tier: int
    neighborhood: str | None = None


class ReasonGenerator(Protocol):
    """The seam tests fake; the real impl wraps the Anthropic client."""

    def generate(self, venue: VenueSummary, archetype: str, mode: str) -> str: ...


def _prompt(venue: VenueSummary, archetype: str, mode: str) -> str:
    tastes = (
        archetype.replace("+", ", ") if archetype != "new" else "still figuring out their taste"
    )
    cuisines = ", ".join(venue.cuisines) or "local food"
    return (
        f"Diner's taste: {tastes}. Mode: {mode}. "
        f"Venue cuisines: {cuisines}. Price tier: {venue.price_tier} of 4. "
        f"Neighborhood: {venue.neighborhood or 'nearby'}. "
        "Write the one-line reason."
    )


class AnthropicReasonGenerator:
    """Real generator. Constructed only by the pre-gen job, never at serve time."""

    def __init__(self, client: anthropic.Anthropic, model: str = DEFAULT_MODEL) -> None:
        self._client = client
        self._model = model

    def generate(self, venue: VenueSummary, archetype: str, mode: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _prompt(venue, archetype, mode)}],
        )
        # Concatenate text blocks; trim stray quotes/whitespace the model adds.
        # `getattr` over isinstance because the fake test client (and the
        # untyped SDK union) only guarantee a `.type == "text"` + `.text` shape.
        text = "".join(
            str(getattr(block, "text", ""))
            for block in message.content
            if getattr(block, "type", "") == "text"
        )
        return text.strip().strip('"').strip()


def build_generator() -> AnthropicReasonGenerator | None:
    """Construct the real generator if a key is configured, else None.

    Returning None is the supported $0 configuration — the pre-gen job no-ops
    and the cache stays empty (templated reasons everywhere).
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic

    return AnthropicReasonGenerator(anthropic.Anthropic())


def pregenerate(
    generator: ReasonGenerator,
    venues: list[VenueSummary],
    archetypes: list[str],
    mode: str,
) -> dict[tuple[str, str, str], str]:
    """Produce cache entries for every (venue, archetype) pair in one mode.

    Keyed by (venue.name-as-id placeholder, archetype, mode) — the caller maps
    venue.name back to the real restaurant id. Pure orchestration: the job
    persists the returned dict into the ReasonCache. A generation that raises
    is skipped (one bad venue must not sink the batch); the templated reason
    remains the fallback for any skipped pair.
    """
    out: dict[tuple[str, str, str], str] = {}
    for venue in venues:
        for archetype in archetypes:
            try:
                out[(venue.name, archetype, mode)] = generator.generate(venue, archetype, mode)
            except Exception:
                continue
    return out
