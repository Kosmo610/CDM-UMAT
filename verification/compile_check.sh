#!/usr/bin/env bash
# compile_check.sh — syntax/interface check of the UMATs without Abaqus.
# Uses a stub ABA_PARAM.INC (Abaqus supplies the real one) that only sets the
# Abaqus implicit-typing convention, then compiles (no link) with gfortran.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
printf '      IMPLICIT REAL*8(A-H,O-Z)\n' > "$TMP/ABA_PARAM.INC"

status=0
for SRC in "$HERE/../src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for" \
           "$HERE/../src/UMAT_CSIC_THERMSHOCK_V3_0.for"; do
  name="$(basename "$SRC")"
  cp "$SRC" "$TMP/umat.f"
  if (cd "$TMP" && gfortran -c -ffixed-form -std=legacy umat.f -o umat.o); then
    echo "COMPILE OK: $name is valid fixed-form Fortran; interfaces resolve."
  else
    echo "COMPILE FAILED: $name"
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  echo
  echo "Next: python3 verification/cross_check_fortran.py"
  echo "  (links the compiled V3_0 subroutines against the verified Python"
  echo "   model -- a clean compile does not mean correct results)"
fi
exit "$status"
