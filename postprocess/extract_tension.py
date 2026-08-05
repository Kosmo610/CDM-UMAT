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
from odbAccess import openOdb

TEN_STEP = 'Tension_23C'
PHASES = ['MATRIX', 'YARN0', 'YARN1', 'YARN2', 'YARN3']
DRIVERS = ['CONSTRAINTSDRIVER0', 'CONSTRAINTSDRIVER1', 'CONSTRAINTSDRIVER2',
           'CONSTRAINTSDRIVER3', 'CONSTRAINTSDRIVER4', 'CONSTRAINTSDRIVER5']
DLAB = ['e_x', 'e_y', 'e_z', 'e_xy', 'e_xz', 'e_yz']
MAT_SDV = [(1, 'DMT'), (2, 'DMC'), (5, 'DMACT')]
YRN_SDV = [(1, 'DY1T'), (3, 'DYTT'), (9, 'DY1'), (10, 'DYT')]
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


def resolve_sdv(names, idx, nm):
    tgt = 'SDV_' + nm
    for n in names:
        if n == tgt:
            return n, 'name'
    cand = [n for n in names if n.startswith(tgt)]
    if cand:
        cand.sort(key=len)
        return cand[0], 'prefix'
    for n in names:
        if n == 'SDV%d' % idx:
            return n, 'num'
    return None, None


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

    sig = [r[3] for r in rows if r[3] != '']
    eps = [r[2] for r in rows if r[3] != '']
    if sig:
        k = max(range(len(sig)), key=lambda i: sig[i])
        log('\n  === 예측 인장 강도 ===')
        log('    최대 응력 %.2f MPa  @  변형률 %.4f %%' % (sig[k], 100 * eps[k]))
        log('    최종점    %.2f MPa  @  변형률 %.4f %%'
            % (sig[-1], 100 * eps[-1]))
        log(peak_verdict(sig, eps, k))
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


def peak_verdict(sig, eps, k):
    """최대점이 진짜 최대인지, 그냥 곡선의 끝인지 판정한다.

    최대점이 마지막 점이면 하중을 더 줄 여지가 있었다는 뜻이므로
    그 값은 강도가 아니라 강도의 하한이다. 이 구분을 놓치면 아직
    상승 중인 곡선을 강도로 잘못 읽게 된다.
    """
    n = len(sig)
    if n < 3:
        return '    [판정] 점이 too few - 판정 불가'
    smax = sig[k]
    drop = (smax - sig[-1]) / smax * 100.0 if smax else 0.0
    tail = max(1, int(0.02 * n))
    if k >= n - tail:
        return ('    [판정] *** 최대점 = 곡선의 끝. 연화 미진입 ***\n'
                '           %.2f MPa 는 강도가 아니라 강도의 하한이다.\n'
                '           목표변형률을 늘려서(속도는 고정) 다시 돌릴 것.'
                % smax)
    if drop < 2.0:
        return ('    [판정] 최대점 통과했으나 하강폭 %.1f%% 로 미미하다.\n'
                '           평탄부일 가능성이 있으니 더 연장하는 편이 안전하다.'
                % drop)
    return ('    [판정] 연화 진입 확인. 최대점 이후 %.1f%% 하강 '
            '(잔여 %d 점).\n           최대응력 %.2f MPa 를 강도로 읽으면 된다.'
            % (drop, n - 1 - k, smax))


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
                    fn, _m = resolve_sdv(names, idx, nm)
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


def main():
    args = sys.argv[1:]
    if not args:
        print('usage: extract_tension.py <job>.odb [--stride N] [--tag NAME] [--step STEPNAME]')
        print('  --tag NAME  writes tension_stress_strainNAME.csv 등으로 파일명을')
        print('              구분한다 (예: --tag _xt500). 병렬 추출 시 덮어쓰기 방지용.')
        print('  --step NAME 인장 Step 이름. 기본 Tension_23C.')
        print('              고온 덱은 --step Tension_500C 처럼 지정한다.')
        sys.exit(1)
    stride = 10
    if '--stride' in args:
        i = args.index('--stride')
        if i + 1 < len(args):
            stride = int(args[i + 1])
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
        log('[1/2] tension_stress_strain%s.csv' % tag)
        write_curve(odb, outdir, V, tag)
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
