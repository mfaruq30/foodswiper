"""Locks the eval-harness stub's contract: it must FAIL loudly until Phase 2.

If someone wires CI to `python -m evalharness.run` before the harness exists,
exit code 2 (not 0) is what stops a scaffold from passing as a working harness.
"""

from evalharness.run import main


def test_stub_refuses_to_pretend_it_works() -> None:
    assert main() == 2
