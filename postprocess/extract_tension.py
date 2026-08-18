# -*- coding: utf-8 -*-
"""
CSiC RVE - 인장 Step 에서 거시 응력-변형 곡선 + 손상 진전 추출

[ 이론 ]
 주기경계 드라이버 절점의 DOF1 이 거시변형률 성분이고
     dW = sum_i RF_i * d(e_i) = V * sum_i sigma_i * d(e_i)
 이므로  sigma_i = RF_i / V.
 인장 Step 에서는 driver0 만 구속하고 1~5 는 자유이므로
 RF_1..RF_5 는 0 이어야 한다(단축 응력상태). 스크립트가 이를 점검한다.

 변형률은 Step 시작값을 뺀 '기계적 변형률' 로 보고한다.
 (driver0 은 냉각 수축 e_x=-2.617e-3 을 이미 갖고 시작하므로,
  빼주지 않으면 곡선이 원점에서 출발하지 않는다.)

사용법:
    abaqus python extract_tension.py CSIC_tension23.odb
    abaqus python extract_tension.py CSIC_tension23.odb --stride 5

출력:
    tension_stress_strain.csv   거시 응력-변형 + 단축성 점검
    tension_damage.csv          변형률별 상(phase)별 손상/응력
    diagnostics_tension.txt
"""
from __future__ import print_function
from __future__ import division

import sys
import os
import re
import csv
import glob
from odbAccess import openOdb

TEN_STEP = 'Tension_23C'
PHASES = ['MATRIX', 'YARN0', 'YARN1', 'YARN2', 'YARN3']
DRIVERS = ['CONSTRAINTSDRIVER0', 'CONSTRAINTSDRIVER1', 'CONSTRAINTSDRIVER2',
           'CONSTRAINTSDRIVER3', 'CONSTRAINTSDRIVER4', 'CONSTRAINTSDRIVER5']
DLAB = ['e_x', 'e_y', 'e_z', 'e_xy', 'e_xz', 'e_yz']
MAT_SDV = [(1, 'DMT'), (2, 'DMC'), (5, 'DMACT')]
# 번호 폴백은 V2_7P 배치 기준 (DYTT 는 2 로 이동). 이름 있는 기존 odb 는
# 이름으로 먼저 잡히므로 영향 없다.
YRN_SDV = [(1, 'DY1T'), (2, 'DYTT'), (9, 'DY1'), (10, 'DYT')]
GEOM_V = 3.5 * 3.5 * 0.44

PY2 = (sys.version_info[0] == 2)
_LOG = []


def log(m):
    print(m)
    _LOG.append(m)


def csv_open(p):
    return open(p, 'wb') if PY2 else open(p, 'w', newline='')


def _sc(v):
    try:
        return v[0]
    except (TypeError, IndexError):
        return v


def fo_keys(fo):
    try:
        return list(fo.keys())
    except Exception:
        return []


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


def get_nset(odb, name):
    ra = odb.rootAssembly
    s = get_set(ra.nodeSets, name)
    if s is not None:
        return s
    for inst in ra.instances.values():
        s = get_set(inst.nodeSets, name)
        if s is not None:
            return s
    return None


def first_node_label(ns):
    nodes = ns.nodes
    if len(nodes) == 0:
        return None
    n0 = nodes[0]
    if hasattr(n0, 'label'):
        return n0.label
    try:
        return n0[0].label
    except (TypeError, IndexError, AttributeError):
        return None


def elset_labels(es):
    out = set()
    els = es.elements
    if len(els) == 0:
        return out
    if hasattr(els[0], 'label'):
        for e in els:
            out.add(e.label)
    else:
        for arr in els:
            for e in arr:
                out.add(e.label)
    return out


def subset_values(field, elset, labels):
    try:
        v = field.getSubset(region=elset).values
        if len(v) > 0:
            return v
    except Exception:
        pass
    return [x for x in field.values if x.elementLabel in labels]


_SDV_SAID = set()


def _stale_swap(names, nm):
    """옛 이름 덱 + V2_7P 이후 UMAT 짝을 잡아 이름을 맞바꾼다.

    V2_7P 가 얀 SV(2)<->SV(3) 을 맞바꿨다 (SDV2 = 횡손상 표시).
    옛 이름 덱(슬롯2=DY1C, 슬롯3=DYTT)으로 V2_7D 를 돌리면 이름이
    옛 자리를 가리켜 DYTT 가 D1C(냉각·인장 내내 0)를 읽는다 --
    P3 t23 에서 실제로 일어났다. V2_7D 표식은 이름 없이 덧붙인
    17번 슬롯이 'SDV17' 로 뜨는 것: 제대로 다시 이름 붙인 덱이라면
    17번도 이름(SDV_YSHR1T)이라 'SDV17' 필드 자체가 없다."""
    if 'SDV17' in names and ('SDV_' + nm) in names:
        if nm == 'DYTT':
            return 'DY1C', True
        if nm == 'DY1C':
            return 'DYTT', True
    return nm, False


def resolve_sdv(names, idx, nm):
    nm, swapped = _stale_swap(names, nm)
    tgt = 'SDV_' + nm
    for n in names:
        if n == tgt:
            return n, ('name-swap' if swapped else 'name')
    cand = [n for n in names if n.startswith(tgt)]
    if cand:
        cand.sort(key=len)
        return cand[0], 'prefix'
    for n in names:
        if n == 'SDV%d' % idx:
            return n, 'num'
    return None, None


def resolve_sdv_logged(names, idx, nm):
    """resolve_sdv + 처음 한 번만 어느 필드를 잡았는지 기록.

    이름 없는 덱(V2_7P)이면 SDV1/SDV2/SDV14 로, 이름 있는 덱이면
    SDV_DMT 식으로 뜬다. 라벨 체계가 의도대로인지 확인용."""
    n, how = resolve_sdv(names, idx, nm)
    if n is not None and nm not in _SDV_SAID:
        _SDV_SAID.add(nm)
        log('  field %-6s -> %s (%s)' % (nm, n, how))
    return n, how


def hr_node_label(hr):
    pt = hr.point
    nd = getattr(pt, 'node', None)
    if nd is not None and getattr(nd, 'label', None) is not None:
        return nd.label
    lab = getattr(pt, 'nodeLabel', None)
    if lab is not None:
        return lab
    m = re.search(r'(\d+)\s*$', str(getattr(hr, 'name', '')))
    return int(m.group(1)) if m else None


def rve_volume(odb, step):
    for st in (step, 'Manufacturing_Cooling'):
        try:
            fr = odb.steps[st].frames[-1]
            if 'IVOL' in fo_keys(fr.fieldOutputs):
                v = 0.0
                for x in fr.fieldOutputs['IVOL'].values:
                    v += _sc(x.data)
                if v > 0:
                    log('  RVE 체적 = %.6f mm^3 (IVOL, step=%s)' % (v, st))
                    return v
        except Exception:
            pass
    log('  RVE 체적 = %.6f mm^3 (기하 대체값)' % GEOM_V)
    return GEOM_V


def write_curve(odb, outdir, V, tag=''):
    step = odb.steps[TEN_STEP]
    labels = {}
    for d in DRIVERS:
        ns = get_nset(odb, d)
        labels[d] = first_node_label(ns) if ns is not None else None
    by = {}
    for hn in step.historyRegions.keys():
        hr = step.historyRegions[hn]
        lab = hr_node_label(hr)
        if lab is None:
            continue
        ho = hr.historyOutputs
        by[lab] = (ho['U1'].data if 'U1' in ho else None,
                   ho['RF1'].data if 'RF1' in ho else None)
    ser = [by.get(labels[d], (None, None)) for d in DRIVERS]
    if ser[0][0] is None:
        log('  [error] driver0 의 U1 history 를 못 읽음')
        return None
    U0, R0 = ser[0]
    n = len(U0)
    e0 = U0[0][1]
    log('  증분 수 %d,  Step 시작 e_x = %.6e (냉각 수축분, 이후 이 값을 뺌)'
        % (n, e0))

    rows = []
    for i in range(n):
        t = U0[i][0]
        eps = U0[i][1] - e0
        sig = (R0[i][1] / V) if (R0 and i < len(R0)) else ''
        row = [i, t, eps, sig]
        off = 0.0
        for k in range(1, 6):
            u, r = ser[k]
            uv = (u[i][1] - u[0][1]) if (u and i < len(u)) else ''
            rv = (r[i][1] / V) if (r and i < len(r)) else ''
            row += [uv, rv]
            if rv != '':
                off = max(off, abs(rv))
        row.append(off)
        rows.append(row)

    hdr = ['Increment', 'StepTime', 'eps_xx_mech', 'sigma_xx_MPa']
    for k in range(1, 6):
        hdr += [DLAB[k] + '_strain', DLAB[k] + '_stress_MPa']
    hdr.append('max_abs_transverse_stress_MPa')
    p = os.path.join(outdir, 'tension_stress_strain%s.csv' % tag)
    f = csv_open(p)
    try:
        w = csv.writer(f)
        w.writerow(hdr)
        for r in rows:
            w.writerow(r)
    finally:
        f.close()
    log('  wrote %s' % p)

    # ---- span 진단: 다른 온도의 덱을 같은 span 으로 맞출 때 필요하다 ----
    #   드라이버는 스텝 안에서 선형 램프이므로 eps/(진행분율) 이 상수이고,
    #   그 값이 곧 "스텝을 완주했을 때의 기계변형률 span" 이다.
    #   중단된 런에서도 맞는 값이 나온다 (0.77 에서 멈춰도 동일).
    #   **스텝시간으로 나누면 안 된다** -- 이 덱들은 스텝 주기가 1.0 도
    #   있고 2.0 도 있어서, 주기로 정규화해야 값이 맞는다.
    period = getattr(step, 'timePeriod', None)
    if not period or period <= 0:
        period = 1.0
    tt = [(r[1], r[2]) for r in rows if r[1] and r[1] > 0.0]
    if tt:
        frac = tt[-1][0] / period
        span = tt[-1][1] / frac
        done = tt[-1][0]
        log('  step time  %.4f / %.4f  (진행 %.1f%%)%s'
            % (done, period, 100.0 * frac,
               '' if frac > 0.999 else '   <-- 중단됨 (완주 아님)'))
        log('  완주 기준 span = %.8f   (eps / 진행분율, 선형 램프)' % span)
        log('  다른 span 으로 다시 돌리려면 덱의')
        log('    *Boundary  ConstraintsDriver0, 1, 1, <목표>')
        log('  를 이렇게 고친다:')
        log('    새 목표 = 현재 목표 + (원하는 span - %.8f)' % span)

    sig = [r[3] for r in rows if r[3] != '']
    eps = [r[2] for r in rows if r[3] != '']
    if sig:
        k = max(range(len(sig)), key=lambda i: sig[i])
        log('\n  === 예측 인장 강도 ===')
        log('    최대 응력 %.2f MPa  @  변형률 %.4f %%' % (sig[k], 100 * eps[k]))
        log('    최종점    %.2f MPa  @  변형률 %.4f %%'
            % (sig[-1], 100 * eps[-1]))
        lp = local_peak(sig)
        if lp is not None and lp != k:
            log('    [강도] 국부최대 %.2f MPa @ 변형률 %.4f %%'
                % (sig[lp], 100 * eps[lp]))
            log('           (첫 하중 급강하 직전. 전역최대 %.2f 는 재상승'
                % sig[k])
            log('            구간의 값이므로 강도가 아니다.)')
        log(peak_verdict(sig, eps, k, lp))
        if len(sig) > 3 and eps[3] != 0:
            log('    초기 접선계수 %.1f GPa  (첫 증분 기준, 증분크기에 민감)'
                % (sig[3] / eps[3] / 1e3))
        for w in (5.0e-4, 1.0e-3):
            e_sec, s_sec = secant(sig, eps, w)
            if e_sec:
                log('    할선계수 0~%.2f%% : %.1f GPa  (증분크기 무관, 비교용)'
                    % (100 * w, s_sec / e_sec / 1e3))
        mo = max(r[-1] for r in rows if r[-1] != '')
        log('    단축성 점검: |횡방향 거시응력| 최대 %.3e MPa  (%.1e x sigma_xx)'
            % (mo, mo / max(sig) if max(sig) else 0))
        log('      -> 0 에 가까우면 driver 1-5 가 자유롭게 풀려 단축 응력상태 성립')
    return rows


def secant(sig, eps, window):
    """0 ~ window 변형률 구간의 할선계수용 (eps, sig).

    첫 증분 기준 접선계수는 증분 크기에 따라 크게 흔들리므로, 해석끼리
    비교할 때는 고정된 변형률 구간의 할선을 써야 한다.
    """
    best = None
    for e, s in zip(eps, sig):
        if e is None or e <= 0.0:
            continue
        if e <= window:
            best = (e, s)
        else:
            break
    return best if best else (None, None)


def local_peak(sig, win=25, dropfrac=0.03):
    """첫 하중 급강하 직전의 국부최대 index. 없으면 None.

    이 RVE 곡선은 "상승 -> 급강하 -> 재상승" 모양이 반복된다.
    재상승은 DMAX 상한 때문에 남는 잔류강성이 만드는 것이고, 실제
    시편은 첫 급강하 지점에서 끊어진다. 따라서 물리적 강도는 전역
    최대가 아니라 이 국부최대다. 실제로 1000 C 런은 재상승이 국부
    최대를 넘어서서(128.32 > 122.19) 전역최대를 쓰면 잘못 읽힌다.
    """
    n = len(sig)
    if n < 2 * win + 2:
        return None
    for i in range(win, n - win):
        if sig[i] <= 0.0:
            continue
        if sig[i] == max(sig[i - win:i + win + 1]):
            if min(sig[i:]) < sig[i] * (1.0 - dropfrac):
                return i
    return None


def end_slope(sig, eps, frac=0.10):
    """곡선 끝 frac 구간의 할선 기울기 [MPa/strain]."""
    n = len(sig)
    i0 = max(0, int((1.0 - frac) * n) - 1)
    de = eps[-1] - eps[i0]
    if de <= 0.0:
        return 0.0
    return (sig[-1] - sig[i0]) / de


def peak_verdict(sig, eps, k, lp=None):
    """최대점이 진짜 최대인지, 곡선의 끝인지, 되올라오는 국부최대인지.

    최대점이 마지막 점이면 하중을 더 줄 여지가 있었다는 뜻이므로 그
    값은 강도가 아니라 강도의 하한이다.

    하강했더라도 끝에서 다시 상승 중이면 그것도 국부최대일 뿐이다.
    손상이 한 번 몰리며 응력이 떨어졌다가 남은 건전부가 하중을 받아
    다시 올라오는 형태인데, 이때 최대점을 강도로 읽으면 곡선을 더
    끌었을 때 그 값을 넘어설 수 있다. 실제로 V2_6 GF 런이 0.282%
    에서 139.4 로 떨어진 뒤 0.365% 에서 124.1 을 찍고 끝(0.545%)에는
    135.9 까지 되올라와 있었다.
    """
    n = len(sig)
    if n < 3:
        return '    [판정] 점이 부족해 판정 불가'
    smax = sig[k]
    if smax <= 0.0:
        return '    [판정] 최대응력이 0 이하 - 판정 불가'
    drop = (smax - sig[-1]) / smax * 100.0
    tail = max(1, int(0.02 * n))
    esl = end_slope(sig, eps)
    e0, s0 = secant(sig, eps, 5.0e-4)
    ref = (s0 / e0) if (e0 and s0) else 0.0
    rising = ref > 0.0 and esl > 0.05 * ref

    if k >= n - tail:
        if lp is not None and lp != k:
            # 급강하를 이미 겪고 재상승해 전역최대가 끝에 온 경우.
            # 강도는 확보되었으므로 더 돌릴 필요가 없다.
            return ('    [판정] 급강하를 이미 지났고 재상승 중이라 전역최대가\n'
                    '           곡선의 끝(%.2f MPa)에 왔다. 강도는 위의\n'
                    '           국부최대 %.2f MPa 로 확정된다. 더 끌 필요 없다.'
                    % (smax, sig[lp]))
        return ('    [판정] *** 최대점 = 곡선의 끝. 연화 미진입 ***\n'
                '           %.2f MPa 는 강도가 아니라 강도의 하한이다.\n'
                '           목표변형률을 늘려서(속도는 고정) 다시 돌릴 것.'
                % smax)
    if rising:
        smin = min(sig[k:])
        return ('    [판정] *** 하강 후 재상승 ***\n'
                '           %.2f -> 최저 %.2f -> 최종 %.2f MPa,\n'
                '           끝 10%% 구간이 %.1f GPa 로 아직 오르는 중이다.\n'
                '           재상승은 DMAX 상한이 남기는 잔류강성 때문이며\n'
                '           실제 시편은 급강하 지점에서 끊어진다.\n'
                '           -> 위의 [강도] 국부최대를 강도로 읽을 것.'
                % (smax, smin, sig[-1], esl / 1e3))
    if drop < 2.0:
        return ('    [판정] 최대점 통과했으나 하강폭 %.1f%% 로 미미하다.\n'
                '           평탄부일 가능성이 있으니 더 연장하는 편이 안전하다.'
                % drop)
    return ('    [판정] 연화 진입 확인. 최대점 이후 %.1f%% 하강 '
            '(잔여 %d 점),\n           끝 기울기 %.1f GPa.  최대응력 %.2f MPa '
            '를 강도로 읽으면 된다.'
            % (drop, n - 1 - k, esl / 1e3, smax))


def write_damage(odb, outdir, V, stride, tag=''):
    step = odb.steps[TEN_STEP]
    frames = list(step.frames)
    idxs = list(range(0, len(frames), max(1, stride)))
    if idxs[-1] != len(frames) - 1:
        idxs.append(len(frames) - 1)
    labels = {}
    ns = get_nset(odb, DRIVERS[0])
    d0 = first_node_label(ns) if ns else None

    p = os.path.join(outdir, 'tension_damage%s.csv' % tag)
    f = csv_open(p)
    try:
        w = csv.writer(f)
        w.writerow(['Frame', 'StepTime', 'eps_xx_mech', 'ElementSet',
                    'LOC_S11_avg', 'LOC_S22_avg', 'LOC_Mises_avg',
                    'LOC_MaxPrin_avg', 'DMT_avg', 'DMT_max', 'DMC_avg',
                    'DMACT_avg', 'DMACT_max', 'DY1T_avg', 'DY1T_max',
                    'DYTT_avg', 'DYTT_max', 'DY1_avg', 'DYT_avg', 'DYT_max',
                    'PctDamaged', 'PctDamaged_Long', 'PctDamaged_Trans'])
        e_ref = None
        for c, fi in enumerate(idxs):
            fr = frames[fi]
            eps = ''
            if d0 is not None and 'U' in fo_keys(fr.fieldOutputs):
                for v in fr.fieldOutputs['U'].values:
                    if v.nodeLabel == d0:
                        val = _sc(v.data)
                        if e_ref is None:
                            e_ref = val
                        eps = val - e_ref
                        break
            log('    frame %d/%d  eps=%s' % (c + 1, len(idxs), eps))
            names = fo_keys(fr.fieldOutputs)
            S = fr.fieldOutputs['S']
            ivol = fr.fieldOutputs['IVOL'] if 'IVOL' in names else None
            for ph in PHASES:
                es = get_elset(odb, ph)
                if es is None:
                    continue
                lab = elset_labels(es)
                sv = subset_values(S, es, lab)
                Sd = dict(((x.elementLabel, x.integrationPoint), x)
                          for x in sv)
                IV = {}
                if ivol is not None:
                    for x in subset_values(ivol, es, lab):
                        IV[(x.elementLabel, x.integrationPoint)] = _sc(x.data)
                isM = (ph == 'MATRIX')
                sl = MAT_SDV if isM else YRN_SDV
                maps = {}
                for idx, nm in sl:
                    fn, _m = resolve_sdv_logged(names, idx, nm)
                    if fn is None:
                        maps[nm] = {}
                        continue
                    maps[nm] = dict(
                        ((x.elementLabel, x.integrationPoint), _sc(x.data))
                        for x in subset_values(fr.fieldOutputs[fn], es, lab))
                dn = 'DMACT' if isM else 'DYT'
                acc = dict((k, 0.0) for k in
                           ['v', 's11', 's22', 'mi', 'mp'])
                sacc = dict((nm, 0.0) for _, nm in sl)
                smax = dict((nm, None) for _, nm in sl)
                nd = 0
                ndl = 0
                ndt = 0
                ne = 0
                for k, x in Sd.items():
                    vol = IV.get(k, 1.0)
                    if vol <= 0:
                        continue
                    acc['v'] += vol
                    acc['s11'] += x.data[0] * vol
                    acc['s22'] += x.data[1] * vol
                    acc['mi'] += x.mises * vol
                    acc['mp'] += x.maxPrincipal * vol
                    ne += 1
                    for _, nm in sl:
                        val = maps[nm].get(k)
                        if val is None:
                            continue
                        sacc[nm] += val * vol
                        if smax[nm] is None or val > smax[nm]:
                            smax[nm] = val
                    dv = maps.get(dn, {}).get(k)
                    if dv is not None and dv > 0.01:
                        nd += 1
                    # mode-wise damaged-element counts (yarns only) so the
                    # longitudinal / transverse percentages can be compared
                    # against Zhang 2022 Fig.11 directly.
                    if not isM:
                        dl = maps.get('DY1T', {}).get(k)
                        if dl is not None and dl > 0.01:
                            ndl += 1
                        dt_ = maps.get('DYTT', {}).get(k)
                        if dt_ is not None and dt_ > 0.01:
                            ndt += 1
                if acc['v'] <= 0:
                    continue
                Vv = acc['v']
                g = lambda nm, kind: (
                    (sacc[nm] / Vv) if kind == 'a' else smax[nm]
                ) if nm in sacc else ''
                w.writerow([fi, fr.frameValue, eps, ph,
                            acc['s11'] / Vv, acc['s22'] / Vv,
                            acc['mi'] / Vv, acc['mp'] / Vv,
                            g('DMT', 'a'), g('DMT', 'm'), g('DMC', 'a'),
                            g('DMACT', 'a'), g('DMACT', 'm'),
                            g('DY1T', 'a'), g('DY1T', 'm'),
                            g('DYTT', 'a'), g('DYTT', 'm'),
                            g('DY1', 'a'), g('DYT', 'a'), g('DYT', 'm'),
                            100.0 * nd / ne if ne else '',
                            (100.0 * ndl / ne) if (ne and not isM) else '',
                            (100.0 * ndt / ne) if (ne and not isM) else ''])
    finally:
        f.close()
    log('  wrote %s' % p)


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
    if not args:
        print('usage: extract_tension.py <job>.odb [--stride N] [--tag NAME] [--step STEPNAME]')
        print('  --tag NAME  writes tension_stress_strainNAME.csv 등으로 파일명을')
        print('              구분한다 (예: --tag _xt500). 병렬 추출 시 덮어쓰기 방지용.')
        print('  --step NAME 인장 Step 이름. 기본 Tension_23C.')
        print('              고온 덱은 --step Tension_500C 처럼 지정한다.')
        print('  --nodamage  손상 CSV 를 건너뛰고 응력-변형만 뽑는다.')
        print('              돌고 있는 해석을 엿볼 때처럼 최대점만 보면')
        print('              될 때 쓴다. 손상 추출이 훨씬 오래 걸린다.')
        sys.exit(1)
    stride = 10
    if '--stride' in args:
        i = args.index('--stride')
        if i + 1 < len(args):
            stride = int(args[i + 1])
    nodamage = '--nodamage' in args
    tag = ''
    if '--tag' in args:
        i = args.index('--tag')
        if i + 1 < len(args):
            tag = args[i + 1]
    global TEN_STEP
    if '--step' in args:
        i = args.index('--step')
        if i + 1 < len(args):
            TEN_STEP = args[i + 1]
    path = [a for a in args if not a.startswith('--') and not a.isdigit()
            and a != tag and a != TEN_STEP][0]
    outdir = os.path.dirname(os.path.abspath(path)) or '.'
    log('opening %s ...' % path)
    if not check_odb_path(path):
        return 2
    odb = openOdb(path=path, readOnly=True)
    try:
        log('steps: %s' % ', '.join(odb.steps.keys()))
        if TEN_STEP not in odb.steps:
            # --step 을 안 줬거나 온도가 다른 덱이면 Tension_* 을 찾아 쓴다.
            # 없으면 그때 실패시킨다. (예전에는 여기서 바로 죽어서 고온
            # 덱을 --step 없이 돌리면 추출이 통째로 날아갔다.)
            cand = [k for k in odb.steps.keys()
                    if k.upper().startswith('TENSION')]
            if len(cand) == 1:
                log('[info] step "%s" 없음 -> "%s" 자동 선택'
                    % (TEN_STEP, cand[0]))
                TEN_STEP = cand[0]
            else:
                log('[error] step "%s" 없음.' % TEN_STEP)
                if cand:
                    log('        후보가 여러 개다: %s' % ', '.join(cand))
                    log('        --step 으로 하나를 지정할 것.')
                sys.exit(2)
        log('tension step = %s' % TEN_STEP)
        V = rve_volume(odb, TEN_STEP)
        n = 1 if nodamage else 2
        log('[1/%d] tension_stress_strain%s.csv' % (n, tag))
        write_curve(odb, outdir, V, tag)
        if nodamage:
            log('[--nodamage] 손상 CSV 는 건너뛴다.')
        else:
            log('[2/2] tension_damage%s.csv' % tag)
            write_damage(odb, outdir, V, stride, tag)
    finally:
        odb.close()
        try:
            fh = open(os.path.join(outdir, 'diagnostics_tension%s.txt' % tag), 'w')
            fh.write('\n'.join(_LOG))
            fh.close()
        except Exception:
            pass
    print('done.')


if __name__ == '__main__':
    main()
