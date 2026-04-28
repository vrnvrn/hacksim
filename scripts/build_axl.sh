#!/usr/bin/env bash
# Build the AXL node binary from the submodule at third_party/axl.
# Mirrors the upstream quickstart: go build via the project Makefile.
# Pinned toolchain matches third_party/axl/Makefile (GOTOOLCHAIN=go1.25.5).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AXL_DIR="${REPO_ROOT}/third_party/axl"

if [ ! -d "${AXL_DIR}" ] || [ ! -f "${AXL_DIR}/Makefile" ]; then
  echo "AXL submodule missing at ${AXL_DIR}" >&2
  echo "run: git submodule update --init --recursive" >&2
  exit 1
fi

if ! command -v go >/dev/null 2>&1; then
  echo "Go toolchain is required but was not found on PATH." >&2
  echo "Install Go 1.25.5 or newer. See https://go.dev/doc/install" >&2
  exit 1
fi

GO_VER="$(go version | awk '{print $3}' | sed 's/go//')"
echo "using go ${GO_VER}"

cd "${AXL_DIR}"
make build
echo ""
if [ -x "${AXL_DIR}/node" ]; then
  echo "ok, built ${AXL_DIR}/node"
  "${AXL_DIR}/node" --help 2>&1 | head -5 || true
else
  echo "build appeared to succeed but ${AXL_DIR}/node is not executable" >&2
  exit 1
fi
