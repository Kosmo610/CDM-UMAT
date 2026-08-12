#!/usr/bin/env bash
# compile_check.sh — syntax/interface check of the UMAT without Abaqus.
# Uses a stub ABA_PARAM.INC (Abaqus supplies the real one) that only sets the
# Abaqus implicit-typing convention, then compiles (no link) with gfortran.
#
# usage: compile_check.sh [file.for ...]
#        with no argument, every UMAT in src/ is checked.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -gt 0 ]; then
  FILES=("$@")
else
  FILES=("$HERE"/../src/*.for)
fi
if [ "${#FILES[@]}" -gt 1 ]; then
  RC=0
  for f in "${FILES[@]}"; do
    "$0" "$f" || RC=1
  done
  exit "$RC"
fi
SRC="${FILES[0]}"
TMP="$(mktemp -d)"
printf '      IMPLICIT REAL*8(A-H,O-Z)\n' > "$TMP/ABA_PARAM.INC"
cp "$SRC" "$TMP/umat.f"
cd "$TMP"
if gfortran -c -ffixed-form -ffixed-line-length-72 -std=legacy \
     -Wall -Wno-unused-dummy-argument umat.f -o umat.o 2>"$TMP/warn.txt"; then
  echo "COMPILE OK  $(basename "$SRC")  -- valid fixed-form; interfaces resolve."
  # -ffixed-line-length-72 truncates past column 72 exactly as Abaqus does,
  # so anything that overflowed would show up here as a syntax error.
  if [ -s "$TMP/warn.txt" ]; then
    echo "--- warnings ---"; cat "$TMP/warn.txt"
  fi
  rm -rf "$TMP"
else
  echo "COMPILE FAILED  $(basename "$SRC")"; cat "$TMP/warn.txt"
  rm -rf "$TMP"; exit 1
fi
