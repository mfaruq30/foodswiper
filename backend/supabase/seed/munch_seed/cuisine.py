"""Cuisine canonicalization.

Raw OSM `cuisine=*` tags are free-text, multi-valued ("burger;american;diner")
and inconsistent. Everything downstream — the anchor adjacency map, cuisine
affinity scoring, UI chips — operates on ~40 canonical nodes, so this mapping
is a load-bearing contract: change it only with a version bump, because
`restaurants.cuisines` rows persist its output (raw tags are kept alongside
for re-canonicalization).

CANONICAL_VERSION history:
  1 — initial map, Phase 1 seed.
"""

CANONICAL_VERSION = 1

# Canonical cuisine vocabulary. Keys are raw tag spellings (lowercase),
# values are canonical nodes. Identity mappings are listed explicitly so the
# canonical vocabulary is greppable in one place.
_RAW_TO_CANONICAL: dict[str, str] = {
    # --- identity / core nodes ---
    "american": "american",
    "bagel": "bagel",
    "bakery": "bakery",
    "barbecue": "bbq",
    "breakfast": "breakfast",
    "bubble_tea": "bubble_tea",
    "burger": "burger",
    "cajun": "cajun",
    "caribbean": "caribbean",
    "chicken": "chicken",
    "chinese": "chinese",
    "coffee_shop": "coffee",
    "deli": "deli",
    "dessert": "dessert",
    "diner": "diner",
    "ethiopian": "ethiopian",
    "filipino": "filipino",
    "french": "french",
    "german": "german",
    "greek": "greek",
    "halal": "halal",
    "ice_cream": "dessert",
    "indian": "indian",
    "italian": "italian",
    "japanese": "japanese",
    "korean": "korean",
    "kosher": "kosher",
    "latin_american": "latin",
    "lebanese": "middle_eastern",
    "mediterranean": "mediterranean",
    "mexican": "mexican",
    "middle_eastern": "middle_eastern",
    "noodle": "noodles",
    "peruvian": "peruvian",
    "pizza": "pizza",
    "ramen": "ramen",
    "salad": "salad",
    "sandwich": "sandwich",
    "seafood": "seafood",
    "soul_food": "southern",
    "spanish": "spanish",
    "steak_house": "steakhouse",
    "sushi": "sushi",
    "thai": "thai",
    "turkish": "turkish",
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "vietnamese": "vietnamese",
    # --- common aliases / regional variants -> nearest canonical node ---
    "asian": "pan_asian",
    "bbq": "bbq",
    "brunch": "breakfast",
    "burgers": "burger",
    "cake": "dessert",
    "cantonese": "chinese",
    "coffee": "coffee",
    "crepe": "french",
    "cuban": "caribbean",
    "donut": "dessert",
    "doughnut": "dessert",
    "dominican": "caribbean",
    "dumpling": "chinese",
    "dumplings": "chinese",
    "falafel": "middle_eastern",
    "fish_and_chips": "seafood",
    "fried_chicken": "chicken",
    "gyro": "greek",
    "haitian": "caribbean",
    "hotdog": "american",
    "hot_dog": "american",
    "international": "pan_asian",
    "irish": "american",
    "israeli": "middle_eastern",
    "jamaican": "caribbean",
    "juice": "juice",
    "kebab": "middle_eastern",
    "malaysian": "pan_asian",
    "moroccan": "middle_eastern",
    "pakistani": "indian",
    "pasta": "italian",
    "persian": "middle_eastern",
    "poke": "japanese",
    "portuguese": "spanish",
    "pretzel": "bakery",
    "puerto_rican": "caribbean",
    "regional": "american",
    "russian": "eastern_european",
    "sichuan": "chinese",
    "smoothie": "juice",
    "soba": "japanese",
    "soup": "noodles",
    "steak": "steakhouse",
    "taco": "mexican",
    "taiwanese": "chinese",
    "tapas": "spanish",
    "tea": "bubble_tea",
    "tex-mex": "mexican",
    "ukrainian": "eastern_european",
    "wings": "chicken",
}

# NYC DOHMH `cuisine_description` values use a different vocabulary; map the
# frequent ones so matched-but-cuisineless OSM POIs can be backfilled.
_DOHMH_TO_CANONICAL: dict[str, str] = {
    "american": "american",
    "bagels/pretzels": "bagel",
    "bakery products/desserts": "bakery",
    "barbecue": "bbq",
    "bottled beverages": "juice",
    "caribbean": "caribbean",
    "chicken": "chicken",
    "chinese": "chinese",
    "chinese/japanese": "chinese",
    "coffee/tea": "coffee",
    "creole": "cajun",
    "delicatessen": "deli",
    "donuts": "dessert",
    "eastern european": "eastern_european",
    "ethiopian": "ethiopian",
    "filipino": "filipino",
    "french": "french",
    "frozen desserts": "dessert",
    "german": "german",
    "greek": "greek",
    "hamburgers": "burger",
    "indian": "indian",
    "irish": "american",
    "italian": "italian",
    "japanese": "japanese",
    "jewish/kosher": "kosher",
    "korean": "korean",
    "latin american": "latin",
    "mediterranean": "mediterranean",
    "mexican": "mexican",
    "middle eastern": "middle_eastern",
    "new american": "american",
    "pancakes/waffles": "breakfast",
    "peruvian": "peruvian",
    "pizza": "pizza",
    "salads": "salad",
    "sandwiches": "sandwich",
    "sandwiches/salads/mixed buffet": "sandwich",
    "seafood": "seafood",
    "soul food": "southern",
    "soups/salads/sandwiches": "sandwich",
    "spanish": "spanish",
    "steakhouse": "steakhouse",
    "sushi": "sushi",
    "tex-mex": "mexican",
    "thai": "thai",
    "turkish": "turkish",
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "vietnamese/cambodian/malaysia": "vietnamese",
}


def canonicalize_osm(raw_cuisine_tag: str | None) -> list[str]:
    """Map a raw OSM cuisine tag (possibly "a;b;c") to canonical nodes.

    Unknown spellings are dropped rather than guessed — raw tags persist in
    `cuisines_raw`, so improving this map later loses nothing.
    """
    if not raw_cuisine_tag:
        return []
    out: list[str] = []
    for part in raw_cuisine_tag.lower().split(";"):
        canonical = _RAW_TO_CANONICAL.get(part.strip().replace(" ", "_"))
        if canonical and canonical not in out:
            out.append(canonical)
    return out


def canonicalize_dohmh(description: str | None) -> list[str]:
    """Map a NYC DOHMH cuisine_description to canonical nodes (best effort)."""
    if not description:
        return []
    canonical = _DOHMH_TO_CANONICAL.get(description.strip().lower())
    return [canonical] if canonical else []
