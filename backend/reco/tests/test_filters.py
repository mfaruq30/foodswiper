"""Layer 1 hard filters — each constraint and the D-010 permissive policies."""

from app.filters import hard_filter
from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile


def _restaurant(
    rid: str,
    *,
    lat: float = 40.730,
    lon: float = -73.990,
    metro: str = "nyc",
    open_state: OpenState = OpenState.OPEN,
    dietary: list[str] | None = None,
    price_tier: int = 2,
    price_imputed: bool = False,
) -> Restaurant:
    return Restaurant(
        id=rid,
        name=rid,
        cuisines=["italian"],
        price_tier=price_tier,
        price_imputed=price_imputed,
        lat=lat,
        lon=lon,
        metro=metro,
        dietary_tags=dietary or [],
        open_state=open_state,
        popularity_prior=0.5,
    )


def _ctx(price_ceiling: int | None = None) -> RequestContext:
    return RequestContext(
        mode=Mode.DINE_IN,
        metro="nyc",
        user_lat=40.730,
        user_lon=-73.990,
        max_distance_m=3000,
        price_ceiling=price_ceiling,
    )


def test_metro_and_range_filters() -> None:
    near = _restaurant("near")
    wrong_metro = _restaurant("boston", metro="boston")
    far = _restaurant("far", lat=41.0)  # ~30 km north
    survivors = hard_filter([near, wrong_metro, far], UserProfile(), _ctx())
    assert [r.id for r in survivors] == ["near"]


def test_closed_dropped_unknown_passes() -> None:
    closed = _restaurant("closed", open_state=OpenState.CLOSED)
    unknown = _restaurant("unknown", open_state=OpenState.UNKNOWN)
    survivors = hard_filter([closed, unknown], UserProfile(), _ctx())
    # D-010: UNKNOWN hours must survive (penalized later, not deleted).
    assert [r.id for r in survivors] == ["unknown"]


def test_dietary_conflict_dropped() -> None:
    vegan = _restaurant("vegan", dietary=["vegan"])
    plain = _restaurant("plain")
    user = UserProfile(dietary_flags=["vegan"])
    survivors = hard_filter([vegan, plain], user, _ctx())
    assert [r.id for r in survivors] == ["vegan"]


def test_price_ceiling_permissive_on_imputed() -> None:
    real_pricey = _restaurant("real4", price_tier=4, price_imputed=False)
    imputed_pricey = _restaurant("imp4", price_tier=4, price_imputed=True)
    survivors = hard_filter([real_pricey, imputed_pricey], UserProfile(), _ctx(price_ceiling=2))
    # Real over-ceiling price is dropped; an imputed guess is never hard-filtered.
    assert [r.id for r in survivors] == ["imp4"]
