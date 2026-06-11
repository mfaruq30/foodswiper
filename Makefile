# Munch monorepo task runner.
#
# Windows note: `make` is not installed on the primary dev machine, so every
# target is a thin wrapper over a script that can be invoked directly:
#     bash scripts/verify.sh
# CI and macOS contributors use these targets as documented in README.md.

.PHONY: verify test seed build-ios

## Run every linter, type check, and test suite. The phase gate. CI calls this.
verify:
	bash scripts/verify.sh

## Tests only (skips lint/format/type checks) — for fast inner-loop iteration.
test:
	bash scripts/verify.sh --tests-only

## Seed NYC + Boston restaurants from open data (Geofabrik + city portals).
seed:
	@echo "ERROR: make seed lands in Phase 1 (backend/supabase/seed/)." && exit 1

## Generate the Xcode project from project.yml and build for simulator.
## macOS only — see docs/ARCHITECTURE.md for the Windows-author/macOS-CI split.
build-ios:
	cd ios/Munch && xcodegen generate && \
	xcodebuild -project Munch.xcodeproj -scheme Munch \
		-destination 'generic/platform=iOS Simulator' \
		CODE_SIGNING_ALLOWED=NO build
