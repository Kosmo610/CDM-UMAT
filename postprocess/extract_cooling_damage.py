# -*- coding: utf-8 -*-
"""
냉각/승온 Step 의 손상요소율 이력 추출  (논문 Fig.4 / Fig.6 대응)

논문 Fig.4 는 냉각(1050 -> 23 C) 중 온도별 손상요소율 곡선이다:
  기지        ~1000 C 개시, 845 C 에서 100%
  얀 횡방향    530 C 개시, 23 C 에서 88%
  얀 종방향    ~0%
논문 Fig.6 은 승온(23 -> 시험온도) 중 같은 곡선이며, 논문에서는
승온 중 손상요소율이 "거의 변하지 않는다" (기지 100 유지, 얀 횡
88~89, 얀 종 ~0).

사용법
------
  abaqus python extract_cooling_damage.py <job>.odb
      [--tag NAME] [--stride N] [--step NAME] [--trange A,B]

  기본은 냉각 Step 자동 검색 (기존 동작 그대로).
  Fig.6 용 승온은:  --step Heating_500C   (온도구간은 이름에서 자동)
  직행(DIRECT) 덱 냉각은 1050->500/1000 이므로 --trange 1050,500 지정.

출력
----
  cooling_damage<TAG>.csv    (냉각)  /  heating_damage<TAG>.csv (승온)
    Frame, StepTime, Temp_degC,
    Matrix_PctDamaged, Warp_PctTrans, Weft_PctTrans,
    Warp_PctLong, Weft_PctLong, (상세: set 별 Pct/Long/Trans)

  화면에 논문 Fig.4 (냉각) 또는 Fig.6 (승온) 목표치 대조표를 찍는다.
"""
from __future__ import print_function
from __future__ import division

import sys
import os
import re
import csv
import glob
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


def step_trange(name):
    """Step 이름 -> (시작온도, 끝온도). 모르면 None.
    make_odb_images.py 와 같은 규칙."""
    import re as _re
    u = name.upper()
    if 'COOL' in u:
        return (1050.0, 23.0)
    if 'HEAT' in u:
        m = _re.search(r'(\d{3,4})', u)
        if m:
            return (23.0, float(m.group(1)))
        return None
    return None

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


def check_odb_path(path):
    """odb 를 열기 전에 존재를 확인하고, 없으면 어디에 있는지 알려준다.

    폴더를 헷갈려 다른 디렉터리에서 돌리는 실수가 잦다. 트레이스백
    대신 "이 폴더의 odb" 와 "상위 트리의 odb" 를 찍어 준다.
    """
    if os.path.exists(path):
        return True
    d = os.path.dirname(os.path.abspath(path)) or '.'
    log('[error] 파일이 없다: %s' % path)
    here = sorted(glob.glob(os.path.join(d, '*.odb')))
    if here:
        log('        이 폴더의 odb: %s'
            % ', '.join(os.path.basename(p) for p in here))
    else:
        log('        이 폴더에 odb 가 없다: %s' % d)
    sib = sorted(glob.glob(os.path.join(os.path.dirname(d), '*', '*.odb')))
    if sib:
        log('        상위 트리에서 찾은 odb:')
        for p in sib[:20]:
            log('          %s' % p)
    log('        맞는 폴더로 cd 한 뒤 다시 실행할 것.')
    return False


def main():
    args = sys.argv[1:]
    tag = ''
    stride = 1
    want_step = None
    tr_arg = None
    used = set()
    for k, setter in (('--tag', 'tag'), ('--stride', 'stride'),
                      ('--step', 'step'), ('--trange', 'trange')):
        if k in args:
            i = args.index(k)
            used.add(i)
            if i + 1 < len(args):
                used.add(i + 1)
                v = args[i + 1]
                if setter == 'tag':
                    tag = v
                elif setter == 'stride':
                    stride = max(1, int(v))
                elif setter == 'step':
                    want_step = v
                elif setter == 'trange':
                    tr_arg = v
    paths = [a for i, a in enumerate(args)
             if i not in used and not a.startswith('--')]
    if not paths:
        print('usage: abaqus python extract_cooling_damage.py <odb> '
              '[--tag NAME] [--stride N] [--step NAME] [--trange A,B]')
        return 1
    path = paths[0]
    outdir = os.path.dirname(os.path.abspath(path)) or '.'

    log('opening %s ...' % path)
    heating = False
    if not check_odb_path(path):
        return 2
    odb = openOdb(path=path, readOnly=True)
    try:
        if want_step:
            st = get_set(odb.steps, want_step)
            if st is None:
                log('[error] step %s not in odb. steps: %s'
                    % (want_step, ', '.join(odb.steps.keys())))
                return 2
        else:
            st = get_set(odb.steps, COOL_STEP)
        if st is None:
            cand = [k for k in odb.steps.keys() if 'COOL' in k.upper()]
            if len(cand) == 1:
                st = odb.steps[cand[0]]
                log('[info] using step %s' % cand[0])
            else:
                log('[error] no cooling step found')
                return 2
        # ---- 온도 구간: --trange > 이름 자동 > 기존 냉각 기본 ------------
        if tr_arg:
            p2 = tr_arg.split(',')
            TA, TB = float(p2[0]), float(p2[1])
        else:
            tr = step_trange(st.name)
            if tr is None:
                log('[error] cannot infer temperature range of step %s.'
                    % st.name)
                log('        give --trange A,B (e.g. --trange 23,500)')
                return 2
            TA, TB = tr
        heating = TB > TA
        # 스텝 주기: frameValue 는 0..주기 로 가므로 주기로 나눠야
        # 온도가 맞는다. (승온 2.05 주기 덱에서 23->2026 C 로 찍히던 버그)
        period = getattr(st, 'timePeriod', None)
        if not period or period <= 0:
            fv = [st.frames[i].frameValue for i in range(len(st.frames))]
            period = max(fv) if fv and max(fv) > 0 else 1.0
        log('step  : %s  (%.0f -> %.0f C, %s, period %.4g)'
            % (st.name, TA, TB, 'heating' if heating else 'cooling',
               period))
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
        said = [False]
        for c, fi in enumerate(idxs):
            fr = frames[fi]
            names = list(fr.fieldOutputs.keys())
            f_dmt = resolve_sdv(names, 1, 'DMT')
            f_dy1 = resolve_sdv(names, 1, 'DY1T')
            f_dyt = resolve_sdv(names, 2, 'DYTT')  # 번호는 V2_7P 배치
            if f_dmt is None or f_dyt is None:
                continue
            if not said[0]:
                # 어느 필드를 잡았는지 남긴다. 이름 없는 덱(V2_7P)이면
                # SDV1/SDV2 로, 이름 있는 덱이면 SDV_DMT 식으로 뜬다.
                log('fields: matrix=%s  yarnL=%s  yarnT=%s'
                    % (f_dmt, f_dy1, f_dyt))
                said[0] = True
            temp = TA + (TB - TA) * (fr.frameValue / period)
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
        base = 'heating_damage' if heating else 'cooling_damage'
        out = os.path.join(outdir, '%s%s.csv' % (base, tag))
        f = csv_open(out)
        try:
            w = csv.writer(f)
            w.writerow(hdr)
            for r in rows:
                w.writerow([r.get(k, '') for k in hdr])
        finally:
            f.close()
        log('wrote %s' % out)

        # ---- 논문 대조: 냉각 Fig.4 / 승온 Fig.6 -------------------------
        if rows and not heating:
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
        elif rows and heating:
            # 논문 Fig.6: 승온 중 손상요소율은 "거의 변하지 않는다".
            # 우리의 판정 기준은 절대값이 아니라 시작->끝 변화량이다.
            first, last = rows[0], rows[-1]
            log('')
            log('  === paper Fig.6 comparison (heating %.0f->%.0fC) ==='
                % (TA, TB))
            log('    %-16s %10s %10s %10s   paper' % ('', 'start', 'end',
                                                      'change'))
            for lab, key, ptxt in (
                    ('matrix', 'Matrix_PctDamaged', '100 -> 100'),
                    ('warp trans', 'Warp_PctTrans', '~88 -> ~89'),
                    ('weft trans', 'Weft_PctTrans', '~88 -> ~89'),
                    ('warp long', 'Warp_PctLong', '~0 (tiny rise)'),
                    ('weft long', 'Weft_PctLong', '~0 (tiny rise)')):
                a, b = first[key], last[key]
                if a == a and b == b:
                    log('    %-16s %9.1f%% %9.1f%% %+9.2f%%   %s'
                        % (lab, a, b, b - a, ptxt))
            log('    (paper: no distinct damage extension during'
                ' heating)')
    finally:
        odb.close()
        try:
            fh = open(os.path.join(outdir, 'diagnostics_%s%s.txt'
                                   % ('heating' if heating else 'cooling',
                                      tag)), 'w')
            fh.write('\n'.join(_LOG))
            fh.close()
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
