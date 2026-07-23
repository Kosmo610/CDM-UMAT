#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_cyclic_deck.py
===================
Generate a REPEATED THERMAL-CYCLE deck from a monotonic CSIC_ZHANG2022 base
deck, for the novelty study "stiffness/strength degradation vs thermal cycles".

Loading history produced:
    COOL 1050 -> 23         (manufacturing TRS, kept from the base deck)
    [ HEAT 23 -> Tmax ; COOL Tmax -> 23 ] x Ncyc     (uniform thermal cycling)
    TENSION at 23           (measures the residual stiffness/strength)

This is "Path A": it reuses the already-verified monotonic UMAT
(UMAT_CSIC_ZHANG2022_V3_1_FAST.for). Cycle-to-cycle damage accumulation
comes from RVE stress redistribution around failed elements (the A03
mechanism), so NO new constitutive code is required to get a first
degradation-vs-N curve. Run several jobs with Ncyc = 1, 2, 5, 10, ... to
trace the curve.

Usage:
    python make_cyclic_deck.py --base CSIC_ZHANG2022_0023C.inp \
           --tmax 1000 --ncyc 5 --out CSIC_CYCLE_1000C_N5.inp

Notes:
  * The base deck's COOL step already writes restart, so intermediate
    states are recoverable.
  * Uniform temperature field (all nodes) => thermal FATIGUE (CTE-mismatch
    driven), consistent with the plan's "uniform cycle" backbone.
  * Macroscopically free thermal expansion during the thermal steps
    (ConstraintsDriver dofs are left free; MasterNode1 fixes rigid body).
"""
import argparse
import re
import sys

COOL_START_RE = re.compile(r'^\*Step,\s*Name=COOL_1050_TO_23', re.IGNORECASE)
TENSION_START_RE = re.compile(r'^\*Step,\s*Name=TENSION', re.IGNORECASE)
STEP_RE = re.compile(r'^\*Step\b', re.IGNORECASE)
ENDSTEP_RE = re.compile(r'^\*End Step\b', re.IGNORECASE)


def find_block(lines, start_idx):
    """Return index (inclusive) of the *End Step closing the step at start_idx."""
    for j in range(start_idx + 1, len(lines)):
        if ENDSTEP_RE.match(lines[j].strip()):
            return j
    raise RuntimeError('Unterminated *Step starting at line %d' % (start_idx + 1))


def thermal_step(name, t_target, tp_name='TP_COOL'):
    """One uniform-temperature *Static thermal step (free macro expansion)."""
    return [
        '*Step, Name=%s, nlgeom=NO, inc=20000' % name,
        'Uniform thermal half-cycle to %g C (free macroscopic expansion)' % t_target,
        '*Static',
        '0.001, 1.0, 1.0E-12, 0.0025',
        '*Controls, parameters=time incrementation',
        '8, 10, , 30, , , , 20, , ,',
        '*Controls, parameters=field, field=displacement',
        ', 0.08',
        '*Controls, parameters=line search',
        '5',
        '*Temperature',
        'AllNodes, %g.' % t_target if float(t_target).is_integer() else 'AllNodes, %g' % t_target,
        '*Output, field, time points=%s' % tp_name,
        '*Element Output, directions=YES',
        'S, PEEQ, IVOL, SDV',
        '*Node Output',
        'U, RF, NT',
        '*Output, history, frequency=1',
    ] + _cd_history() + [
        '*Restart, write, number interval=1, time marks=NO',
        '*End Step',
    ]


def _cd_history():
    out = []
    for k in range(6):
        out += ['*Node Output, nset=ConstraintsDriver%d' % k, 'U, V, RF']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='monotonic base .inp (0023C recommended)')
    ap.add_argument('--tmax', type=float, required=True, help='peak cycle temperature (C)')
    ap.add_argument('--ncyc', type=int, required=True, help='number of thermal cycles')
    ap.add_argument('--out', required=True, help='output .inp path')
    a = ap.parse_args()

    with open(a.base, 'r') as f:
        text = f.read()
    lines = text.splitlines()

    cool_start = tension_start = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if cool_start is None and COOL_START_RE.match(s):
            cool_start = i
        if TENSION_START_RE.match(s):
            tension_start = i
            break
    if cool_start is None or tension_start is None:
        sys.exit('ERROR: could not locate COOL and/or TENSION steps in base deck.')

    cool_end = find_block(lines, cool_start)          # *End Step of COOL
    # Sanity: the base deck must be COOL ... TENSION (0023C). If a HEAT step
    # sits between, the base is a 500/1000 deck; require the 0023C base.
    between = '\n'.join(lines[cool_end + 1:tension_start])
    if STEP_RE.search('\n'.join('*' + p for p in between.split('*'))) and 'Name=HEAT' in between:
        sys.exit('ERROR: use the 0023C base deck (COOL -> TENSION, no HEAT step).')

    prefix = lines[:cool_end + 1]                     # mesh + materials + COOL
    tension_block = lines[tension_start:]             # final residual-tension step

    cyc = []
    for n in range(1, a.ncyc + 1):
        cyc += thermal_step('HEAT_23_TO_%d_C%d' % (int(a.tmax), n), a.tmax)
        cyc += thermal_step('COOL_%d_TO_23_C%d' % (int(a.tmax), n), 23)

    out_lines = prefix + cyc + tension_block
    with open(a.out, 'w') as f:
        f.write('\n'.join(out_lines) + '\n')

    n_steps = sum(1 for ln in out_lines if STEP_RE.match(ln.strip()))
    n_ends = sum(1 for ln in out_lines if ENDSTEP_RE.match(ln.strip()))
    print('Wrote %s' % a.out)
    print('  cycles           : %d  (Tmax=%g C)' % (a.ncyc, a.tmax))
    print('  *Step / *End Step : %d / %d  (must match)' % (n_steps, n_ends))
    print('  total steps       : COOL + %d*2 thermal + TENSION = %d' %
          (a.ncyc, 2 + 2 * a.ncyc))
    if n_steps != n_ends:
        sys.exit('ERROR: *Step/*End Step mismatch -- deck is malformed.')


if __name__ == '__main__':
    main()
