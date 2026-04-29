.PHONY: help test web-test build-axl gen-keys demo smoke hooks-install clean

help:
	@echo "HackSim, an Agent Town on Gensyn AXL"
	@echo ""
	@echo "  make hooks-install   set core.hooksPath to .githooks (writing rules enforcement)"
	@echo "  make test            run python unit tests"
	@echo "  make web-test        run web unit tests"
	@echo "  make build-axl       build the AXL Go binary in third_party/axl"
	@echo "  make gen-keys        generate ed25519 keys for the default agent count"
	@echo "  make demo            launch orchestrator + frontend together (live)"
	@echo "  make smoke           headless end-to-end smoke (no browser)"
	@echo "  make clean           remove sim-runs and node-keys directories"

test:
	pytest -q

web-test:
	cd apps/web && pnpm test --run

build-axl:
	bash scripts/build_axl.sh

gen-keys:
	bash scripts/gen_keys.sh

demo:
	bash scripts/run_demo.sh

smoke:
	.venv/bin/python scripts/smoke_e2e.py

hooks-install:
	git config core.hooksPath .githooks
	@echo "hooks installed: .githooks/pre-commit and .githooks/commit-msg"

clean:
	rm -rf sim-runs node-keys node-runtime
	@echo "cleaned"
