# -*- coding: utf-8 -*-
"""
냉각 Step 의 손상요소율 이력 추출  (논문 Fig.4 대응)

논문 Fig.4 는 냉각(1050 -> 23 C) 중 온도별 손상요소율 곡선이다:
  기지        ~1000 C 개시, 845 C 에서 100%
  얀 횡방향    530 C 개시, 23 C 에서 88%
  얀 종방향    ~0%

지금까지는 냉각 '종료 시점' 한 장(tension_damage 첫 줄)만 봤다.
이 스크립트는 냉각 Step 의 모든 프레임을 읽어 같은 곡선을 만든다.
PAPERFAITH 배치(P0/P1/P2)의 판정 기준이 바로 이 곡선이다.

사용법
------
  abaqus python extract_cooling_damage.py <job>.odb [--tag NAME] [--stride N]

출력
----
  cooling_damage<TAG>.csv
    Frame, StepTime, Temp_degC,
    Matrix_PctDamaged, Warp_PctTrans, Weft_PctTrans,
    Warp_PctLong, Weft_PctLong, (상세: set 별 Pct/Long/Trans)

  화면에 논문 Fig.4 목표치와의 대조표를 찍는다.
"""
from __future__ import print_function
from __future__ import division

import sys
import os
import re
import csv
from odbAccess import openOdb

COOL_STEP = 'Manufacturing_Cooling'
PHASES = ['MATRIX', 'YARN0', 'YARN1', 'YARN2', 'YARN3']
# 워프 = 하중(x) 방향 얀, 위프 = 직교 얀. 기존 관례와 동일하게
# Yarn0/1 = warp, Yarn2/3 = weft 로 둔다.
WARP = ('YARN0', 'YARN1')
WEFT = ('YARN2', 'YARN3')
DTH = 0.01                      # 손상요소 판정 문턱 (기존 추출과 동일)
T0, T1 = 1050.0, 23.0

# 논문 Fig.4 의 목표치
PAPER = {'m_onset': 1000.0, 'm_100_at': 845.0,
         'y_onset': 530.0, 'y_final': 88.0}

PY2 = (sys.version_info[0] == 2)
_LOG = []


def log(m):
    print(m)
    _LOG.append(str(m))


def csv_open(p):
    return open(p, 'wb') if PY2 else open(p, 'w', newline='')


def _sc(v):
    try:
        return v[0]
    except (TypeError, IndexError):
        return v


def get_set(container, name):
    if name in container:
        return container[name]
    up = name.upper().replace(' ', '')
    for k in container.keys():
        if k.upper().replace(' ', '') == up:
            return container[k]
    return None


def get_elset(odb, name):
    ra = odb.rootAssembly
    s = get_set(ra.elementSets, name)
    if s is not None:
        return s
    for inst in ra.instances.values():
        s = get_set(inst.elementSets, name)
        if s is not None:
            return s
    return None


def resolve_sdv(names, idx, nm):
    tgt = 'SDV_' + nm
    for n in names:
        if n == tgt:
            return n
    cand = [n for n in names if n.startswith(tgt)]
    if cand:
        cand.sort(key=len)
        return cand[0]
    for n in names:
        if n == 'SDV%d' % idx:
            return n
    return None


def pct_over(field, elset, th):
    """elset 에서 SDV 값이 th 를 넘는 적분점 비율 [%]."""
    try:
        vals = field.getSubset(region=elset).values
    except Exception:
        return float('nan')
    n = len(vals)
    if n == 0:
        return float('nan')
    c = 0
    for v in vals:
        if _sc(v.data) > th:
            c += 1
    return 100.0 * c / n


def onset_temp(rows, key):
    """손상률이 처음 0.5% 를 넘는 온도."""
    for r in rows:
        if r[key] == r[key] and r[key] > 0.5:      # nan 방지
            return r['Temp_degC']
    return None


def main():
    args = sys.argv[1:]
    tag = ''
    stride = 1
    if '--tag' in args:
        i = args.index('--tag')
        if i + 1 < len(args):
            tag = args[i + 1]
    if '--stride' in args:
        i = args.index('--stride')
        if i + 1 < len(args):
            stride = max(1, int(args[i + 1]))
    paths = [a for a in args if not a.startswith('--')
             and a != tag and not a.isdigit()]
    if not paths:
        print('usage: abaqus python extract_cooling_damage.py <odb> '
              '[--tag NAME] [--stride N]')
        return 1
    path = paths[0]
    outdir = os.path.dirname(os.path.abspath(path)) or '.'

    log('opening %s ...' % path)
    odb = openOdb(path=path, readOnly=True)
    try:
        st = get_set(odb.steps, COOL_STEP)
        if st is None:
            cand = [k for k in odb.steps.keys() if 'COOL' in k.upper()]
            if len(cand) == 1:
                st = odb.steps[cand[0]]
                log('[info] using step %s' % cand[0])
            else:
                log('[error] no cooling step found')
                return 2
        sets = {}
        for ph in PHASES:
            es = get_elset(odb, ph)
            if es is None:
                log('[error] elset %s not found' % ph)
                return 2
            sets[ph] = es

        frames = list(st.frames)
        idxs = list(range(0, len(frames), stride))
        if idxs and idxs[-1] != len(frames) - 1:
            idxs.append(len(frames) - 1)
        log('frames: %d (reading %d)' % (len(frames), len(idxs)))

        rows = []
        for c, fi in enumerate(idxs):
            fr = frames[fi]
            names = list(fr.fieldOutputs.keys())
            f_dmt = resolve_sdv(names, 1, 'DMT')
            f_dy1 = resolve_sdv(names, 1, 'DY1T')
            f_dyt = resolve_sdv(names, 3, 'DYTT')
            if f_dmt is None or f_dyt is None:
                continue
            temp = T0 - (T0 - T1) * fr.frameValue
            row = {'Frame': fi, 'StepTime': fr.frameValue,
                   'Temp_degC': temp}
            FD = fr.fieldOutputs
            row['Matrix_PctDamaged'] = pct_over(FD[f_dmt], sets['MATRIX'],
                                                DTH)
            for ph in PHASES[1:]:
                row[ph + '_PctTrans'] = pct_over(FD[f_dyt], sets[ph], DTH)
                row[ph + '_PctLong'] = (pct_over(FD[f_dy1], sets[ph], DTH)
                                        if f_dy1 else float('nan'))

            def avg(keys):
                v = [row[k] for k in keys if row[k] == row[k]]
                return sum(v) / len(v) if v else float('nan')
            row['Warp_PctTrans'] = avg([p + '_PctTrans' for p in WARP])
            row['Weft_PctTrans'] = avg([p + '_PctTrans' for p in WEFT])
            row['Warp_PctLong'] = avg([p + '_PctLong' for p in WARP])
            row['Weft_PctLong'] = avg([p + '_PctLong' for p in WEFT])
            rows.append(row)
            if c % 10 == 0 or fi == idxs[-1]:
                log('  frame %3d  T=%7.1f C | matrix %6.2f%% | '
                    'warp-T %6.2f%%  weft-T %6.2f%%'
                    % (fi, temp, row['Matrix_PctDamaged'],
                       row['Warp_PctTrans'], row['Weft_PctTrans']))

        hdr = (['Frame', 'StepTime', 'Temp_degC', 'Matrix_PctDamaged',
                'Warp_PctTrans', 'Weft_PctTrans', 'Warp_PctLong',
                'Weft_PctLong']
               + [p + s for p in PHASES[1:]
                  for s in ('_PctTrans', '_PctLong')])
        out = os.path.join(outdir, 'cooling_damage%s.csv' % tag)
        f = csv_open(out)
        try:
            w = csv.writer(f)
            w.writerow(hdr)
            for r in rows:
                w.writerow([r.get(k, '') for k in hdr])
        finally:
            f.close()
        log('wrote %s' % out)

        # ---- 논문 Fig.4 대조 -------------------------------------------
        if rows:
            last = rows[-1]
            mo = onset_temp(rows, 'Matrix_PctDamaged')
            yo_w = onset_temp(rows, 'Warp_PctTrans')
            yo_f = onset_temp(rows, 'Weft_PctTrans')
            m100 = None
            for r in rows:
                if (r['Matrix_PctDamaged'] == r['Matrix_PctDamaged']
                        and r['Matrix_PctDamaged'] >= 99.5):
                    m100 = r['Temp_degC']
                    break
            log('')
            log('  === paper Fig.4 comparison ===')
            log('    %-28s %10s %10s' % ('', 'paper', 'this run'))
            log('    %-28s %9.0fC %10s' % ('matrix damage onset',
                PAPER['m_onset'], ('%.0fC' % mo) if mo else '-'))
            log('    %-28s %9.0fC %10s' % ('matrix reaches 100%',
                PAPER['m_100_at'], ('%.0fC' % m100) if m100 else 'never'))
            log('    %-28s %9.0fC %10s' % ('yarn transverse onset',
                PAPER['y_onset'],
                ('%.0fC' % max(v for v in (yo_w, yo_f) if v))
                if (yo_w or yo_f) else '-'))
            log('    %-28s %9.0f%% %9.1f%%' % ('yarn transverse at 23C',
                PAPER['y_final'],
                (last['Warp_PctTrans'] + last['Weft_PctTrans']) / 2.0))
            log('    %-28s %10s %9.1f%%' % ('matrix at 23C', '100%',
                last['Matrix_PctDamaged']))
    finally:
        odb.close()
        try:
            fh = open(os.path.join(outdir,
                                   'diagnostics_cooling%s.txt' % tag), 'w')
            fh.write('\n'.join(_LOG))
            fh.close()
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
