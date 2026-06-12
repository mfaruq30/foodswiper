# Committed demo/CI fixtures

`venues.sample.ndjson` — 100 real venues (60 around Washington Square NYC,
40 around BU East Campus Boston) in the canonical artifact format, committed
so CI end-to-end runs and quick local demos need no seed-pipeline run.

**License:** derived from OpenStreetMap (© OpenStreetMap contributors,
[ODbL 1.0](https://www.openstreetmap.org/copyright)) merged with NYC Open
Data and Analyze Boston (PDDL) records, exactly as the full
`seed_out/venues.ndjson`. This file is redistributable under ODbL terms;
per-row `source_license` fields record provenance.

Refresh with the seed pipeline + the snippet in the Phase 4 commit message
(nearest-N selection around the two demo presets).
