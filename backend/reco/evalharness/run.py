"""CLI entry point for the offline eval harness: ``python -m evalharness.run``."""

import sys


def main() -> int:
    """Fail loudly until Phase 2 lands.

    Returning a distinct non-zero code prevents anyone (human or CI) from
    mistaking a scaffold for a working harness.
    """
    sys.stderr.write("munch-reco eval harness is scaffolded; implementation lands in Phase 2\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
