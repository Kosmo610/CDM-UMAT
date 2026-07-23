#!/usr/bin/env bash
# Single material-point verification of UMAT_CSIC_ZHANG2022_V3_1_FAST.for
# Compiles the production UMAT with a stub ABA_PARAM.INC and drives one
# integration point. Confirms: (1) clean compile, (2) matrix/yarn peaks
# match the input strengths, (3) exact consistent tangent (elastic +
# plastic). Requires gfortran only; no Abaqus license needed.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
UMAT="${1:-$HERE/../../src/UMAT_CSIC_ZHANG2022_V3_1_FAST.for}"
echo "UMAT under test: $UMAT"
gfortran -w -ffixed-form -ffixed-line-length-none -I"$HERE/stub" \
    "$HERE/driver.f" "$HERE/stub_util.f" "$UMAT" -o "$HERE/run_umat"
"$HERE/run_umat"
