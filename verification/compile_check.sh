#!/usr/bin/env bash
# compile_check.sh — syntax/interface check of the UMAT without Abaqus.
# Uses a stub ABA_PARAM.INC (Abaqus supplies the real one) that only sets the
# Abaqus implicit-typing convention, then compiles (no link) with gfortran.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for"
TMP="$(mktemp -d)"
printf '      IMPLICIT REAL*8(A-H,O-Z)\n' > "$TMP/ABA_PARAM.INC"
cp "$SRC" "$TMP/umat.f"
cd "$TMP"
if gfortran -c -ffixed-form -std=legacy umat.f -o umat.o; then
  echo "COMPILE OK: UMAT is valid fixed-form Fortran; interfaces resolve."
  rm -rf "$TMP"
else
  echo "COMPILE FAILED"; rm -rf "$TMP"; exit 1
fi
