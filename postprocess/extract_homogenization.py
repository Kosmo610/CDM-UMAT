# -*- coding: utf-8 -*-
"""
손상 후 균질화 강성 6x6 추출  (HOM_* 섭동 스텝)

지금까지 안 뽑고 있던 정보다. 모든 덱은 인장 스텝 뒤에 선형섭동
스텝 6개(HOM_E11/E22/E33/G12/G13/G23)를 갖고 있고, 각 스텝은
드라이버 하나에만 1e-4 를 주고 나머지 5개는 0 으로 고정한 뒤
6개 드라이버의 반력을 전부 기록한다. 즉 강성행렬의 한 열이다.

    C[i][j] = (RF_i / V) / eps_j        eps_j = 1e-4

손상은 freeze_step 때문에 이 스텝들에서 동결되므로, 얻어지는 것은
**인장 손상 직후 상태의 균질화 강성**이다. 이미 끝난 odb 전부에
들어있으니 새 해석이 필요 없다.

무엇에 쓰나
-----------
- 손상으로 강성이 얼마나 떨어졌는지 정량화 (E11 저하율)
- noTRS odb 를 같이 돌리면 무손상 기준 강성을 얻는다
- 온도별 강성 비교 -> 논문의 강성저하 서술과 대조
- 직교이방성이 유지되는지 (대칭성·비대각항) 점검

사용법
------
  abaqus python extract_homogenization.py <job>.odb [--tag NAME]
  abaqus python extract_homogenization.py a.odb b.odb --tag _all   (여러 개 비교)

출력
----
  homogenized_stiffness<TAG>.csv    6x6 C, 공학상수, 저하율
"""
from __future__ import print_function
from __future__ import division

import sys
import os
import re
import csv
import glob
from odbAccess import openOdb

DRIVERS = ['CONSTRAINTSDRIVER0', 'CONSTRAINTSDRIVER1', 'CONSTRAINTSDRIVER2',
           'CONSTRAINTSDRIVER3', 'CONSTRAINTSDRIVER4', 'CONSTRAINTSDRIVER5']
# HOM 스텝 이름 -> 구동한 드라이버 index
HOM = [('HOM_E11', 0), ('HOM_E22', 1), ('HOM_E33', 2),
       ('HOM_G12', 3), ('HOM_G13', 4), ('HOM_G23', 5)]
LAB = ['xx', 'yy', 'zz', 'xy', 'xz', 'yz']
GEOM_V = 3.5 * 3.5 * 0.44

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


def rve_volume(odb):
    for st in odb.steps.keys():
        try:
            fr = odb.steps[st].frames[-1]
            if 'IVOL' in fr.fieldOutputs.keys():
                v = sum(_sc(x.data) for x in fr.fieldOutputs['IVOL'].values)
                if v > 0:
                    return v, st
        except Exception:
            pass
    return GEOM_V, 'geometric fallback'


def invert6(C):
    """6x6 가우스-조던 역행렬. 특이하면 None."""
    n = 6
    A = [list(C[i]) + [1.0 if i == j else 0.0 for j in range(n)]
         for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-30:
            return None
        A[c], A[p] = A[p], A[c]
        d = A[c][c]
        A[c] = [x / d for x in A[c]]
        for r in range(n):
            if r != c and A[r][c] != 0.0:
                f = A[r][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [row[n:] for row in A]


def stiffness(odb, V):
    """HOM_* 스텝에서 6x6 강성을 만든다. 없는 열은 None."""
    labels = {}
    for d in DRIVERS:
        ns = get_nset(odb, d)
        labels[d] = first_node_label(ns) if ns is not None else None

    C = [[None] * 6 for _ in range(6)]
    found = []
    for name, j in HOM:
        key = get_set(odb.steps, name)
        if key is None:
            continue
        st = odb.steps[name] if name in odb.steps else key
        by = {}
        for hn in st.historyRegions.keys():
            hr = st.historyRegions[hn]
            lab = hr_node_label(hr)
            if lab is None:
                continue
            ho = hr.historyOutputs
            by[lab] = (ho['U1'].data if 'U1' in ho else None,
                       ho['RF1'].data if 'RF1' in ho else None)
        if not by:
            # pre.exe 가 모든 Step 정의를 odb 에 미리 써두므로, 실행되지
            # 않은 Step 도 odb.steps 에는 존재한다. history 가 비어 있으면
            # 그 Step 은 실제로 돈 적이 없다는 뜻이다.
            log('  [skip] %s: step exists but never ran '
                '(job stopped before this step)' % name)
            continue
        u, _ = by.get(labels[DRIVERS[j]], (None, None))
        if not u:
            log('  [warn] %s: no U1 history on the driven driver' % name)
            continue
        eps = u[-1][1]
        if abs(eps) < 1e-12:
            log('  [warn] %s: perturbation strain is zero' % name)
            continue
        for i in range(6):
            _, r = by.get(labels[DRIVERS[i]], (None, None))
            if r:
                C[i][j] = (r[-1][1] / V) / eps
        found.append((name, eps))
    return C, found


def engineering(C):
    """C 에서 공학상수. 전부 채워져 있어야 한다."""
    if any(C[i][j] is None for i in range(6) for j in range(6)):
        return None
    S = invert6(C)
    if S is None:
        return None
    out = {}
    for i, k in enumerate(('E11', 'E22', 'E33')):
        out[k] = 1.0 / S[i][i] if S[i][i] else float('nan')
    out['G12'] = 1.0 / S[3][3] if S[3][3] else float('nan')
    out['G13'] = 1.0 / S[4][4] if S[4][4] else float('nan')
    out['G23'] = 1.0 / S[5][5] if S[5][5] else float('nan')
    out['nu12'] = -S[1][0] / S[0][0] if S[0][0] else float('nan')
    out['nu13'] = -S[2][0] / S[0][0] if S[0][0] else float('nan')
    out['nu23'] = -S[2][1] / S[1][1] if S[1][1] else float('nan')
    return out


def asymmetry(C):
    """대칭성 위반 최대값 [%]. 강성은 대칭이어야 한다."""
    worst = 0.0
    for i in range(6):
        for j in range(i + 1, 6):
            a, b = C[i][j], C[j][i]
            if a is None or b is None:
                continue
            m = max(abs(a), abs(b))
            if m > 1.0:
                worst = max(worst, 100.0 * abs(a - b) / m)
    return worst


def process(path):
    log('=' * 70)
    log(' %s' % os.path.basename(path))
    log('=' * 70)
    if not check_odb_path(path):
        return 2
    odb = openOdb(path=path, readOnly=True)
    try:
        V, src = rve_volume(odb)
        log('  RVE volume %.6f mm^3 (from step %s)' % (V, src))
        C, found = stiffness(odb, V)
        if not found:
            log('  [error] no usable HOM_* step in this odb.')
            log('          The job must run PAST the tension step for the')
            log('          six perturbation steps to execute. A job that')
            log('          was stopped during tension has no stiffness.')
            return None
        log('  read %d step(s): %s'
            % (len(found), ', '.join('%s(eps=%.1e)' % f for f in found)))
        log('')
        log('  damaged homogenized stiffness C [MPa]')
        log('        ' + ''.join('%12s' % l for l in LAB))
        for i in range(6):
            row = ''.join(('%12.1f' % C[i][j]) if C[i][j] is not None
                          else '%12s' % '-' for j in range(6))
            log('   %-4s %s' % (LAB[i], row))
        asym = asymmetry(C)
        log('')
        log('  max asymmetry %.3f %%  -> %s'
            % (asym, 'OK' if asym < 2.0 else '*** CHECK ***'))
        eng = engineering(C)
        if eng:
            log('  eng.const  E11 %.1f  E22 %.1f  E33 %.1f GPa'
                % (eng['E11'] / 1e3, eng['E22'] / 1e3, eng['E33'] / 1e3))
            log('            G12 %.1f  G13 %.1f  G23 %.1f GPa'
                % (eng['G12'] / 1e3, eng['G13'] / 1e3, eng['G23'] / 1e3))
            log('            nu12 %.4f  nu13 %.4f  nu23 %.4f'
                % (eng['nu12'], eng['nu13'], eng['nu23']))
        log('')
        return dict(name=os.path.basename(path), V=V, C=C, asym=asym, eng=eng)
    finally:
        odb.close()


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
    if '--tag' in args:
        i = args.index('--tag')
        if i + 1 < len(args):
            tag = args[i + 1]
    paths = [a for a in args if not a.startswith('--') and a != tag]
    if not paths:
        print('usage: abaqus python extract_homogenization.py <odb> [...] '
              '[--tag NAME]')
        return 1

    outdir = os.path.dirname(os.path.abspath(paths[0])) or '.'
    res = [r for r in (process(p) for p in paths) if r]
    if not res:
        return 2

    p = os.path.join(outdir, 'homogenized_stiffness%s.csv' % tag)
    f = csv_open(p)
    try:
        w = csv.writer(f)
        w.writerow(['odb', 'RVE_volume_mm3', 'asymmetry_pct']
                   + ['C_%s%s' % (LAB[i], LAB[j])
                      for i in range(6) for j in range(6)]
                   + ['E11', 'E22', 'E33', 'G12', 'G13', 'G23',
                      'nu12', 'nu13', 'nu23'])
        for r in res:
            row = [r['name'], '%.6f' % r['V'], '%.4f' % r['asym']]
            row += [('%.4f' % r['C'][i][j]) if r['C'][i][j] is not None else ''
                    for i in range(6) for j in range(6)]
            e = r['eng']
            row += [('%.4f' % e[k]) if e else '' for k in
                    ('E11', 'E22', 'E33', 'G12', 'G13', 'G23',
                     'nu12', 'nu13', 'nu23')]
            w.writerow(row)
    finally:
        f.close()
    log('wrote %s' % p)

    if len(res) > 1:
        log('')
        log(' comparison (E11)')
        base = res[0]['eng']['E11'] if res[0]['eng'] else None
        for r in res:
            if not r['eng']:
                continue
            d = ('  (%+.1f%%)' % (100.0 * (r['eng']['E11'] / base - 1.0))
                 if base else '')
            log('   %-34s E11 %8.1f GPa%s'
                % (r['name'], r['eng']['E11'] / 1e3, d))

    try:
        fh = open(os.path.join(outdir, 'diagnostics_homog%s.txt' % tag), 'w')
        fh.write('\n'.join(_LOG))
        fh.close()
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
