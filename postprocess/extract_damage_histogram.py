# -*- coding: utf-8 -*-
"""
상.모드별 손상변수 히스토그램 추출  (논문 Fig.A1/A2/A3 대응)

논문 부록 Fig.A1-A3 는 각 하중 단계에서 5개 그룹의 손상변수 "값" 분포
히스토그램을 준다:
  기지 손상 / 워프 종방향 / 워프 횡방향 / 위프 종방향 / 위프 횡방향
각 판에 "sum: XX%" (손상요소율) 이 함께 적혀 있어, 손상요소율(개수)과
손상변수 크기(심각도)를 분리해서 대조할 수 있는 유일한 데이터다.

지금까지 우리는 손상요소율과 평균값만 뽑았고 분포는 버렸다.
이 스크립트가 그 공백을 채운다.

사용법
------
  abaqus python extract_damage_histogram.py <job>.odb
      [--step NAME] [--frames a,b,c] [--tag NAME]

  --step   기본: Tension_* 자동 검색, 없으면 냉각 Step
  --frames 기본: 해당 Step 의 마지막 프레임 1개
           (논문 단계점 I/II/III 대조는 프레임 번호를 직접 지정)

출력
----
  damage_hist<TAG>_f<NN>.csv   프레임당 1개
    BinLo, BinHi, Matrix, Warp_Long, Warp_Trans, Weft_Long, Weft_Trans
    (각 칸 = 그 구간 요소수 / 그룹 전체 요소수 * 100 [%])
  화면에 sum(손상요소율)/평균/p95 를 논문 대조용으로 찍는다.

  yarn_shear_frac<TAG>_f<NN>.csv   (V2_7D SDV17 이 있는 odb 에서만)
    얀 종방향 인장이 **무엇 때문에** 개시했는지의 분포.
    0 = σ11 단독, 1 = 전단 단독.

주의 — SDV17 은 반드시 걸러서 읽는다
------------------------------------
`SDV17 = 0` 은 두 가지를 뜻한다: "σ11 이 혼자 죽였다" 와
"1T 모드가 개시조차 안 했다". 그래서 이 스크립트는 항상
**`SDV5(=R1T) >= 1`** 인 적분점만 집계한다. 안 거르면 미개시
요소가 전부 "σ11 주도" 로 잡혀 결론이 뒤집힌다.

V2_7D 이전 odb 에는 SDV17 이 없다. 그 경우 이 절만 건너뛰고
나머지는 그대로 나온다 — 기존 odb 재추출이 깨지지 않는다.

논문 대조 기준값 (Fig.A1-A3 판독):
  23C  최대점(III): 기지 sum 100% (d 0.4~0.8), 워프종 60.67%,
       워프횡 99.77%, 위프종 2.40%, 위프횡 99.29%
  500C 최대점(IV): 워프종 44.38%, 워프횡 95.83%, 위프종 3.38%,
       위프횡 99.59%
  1000C 최대점(IV): 워프종 32.12%, 워프횡 89.06%, 위프종 14.28%,
       위프횡 99.17%
"""
from __future__ import print_function
from __future__ import division

import sys
import os
import io
import csv
import glob
from odbAccess import openOdb

WARP = ('YARN0', 'YARN1')
WEFT = ('YARN2', 'YARN3')
DTH = 0.01                    # 손상요소 판정 문턱 (기존 추출과 동일)
NBIN = 20                     # 0.05 폭 x 20 = 0~1.0
PY2 = (sys.version_info[0] == 2)


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


# ---- 얀 SDV 배치 판정 (옛/새) ------------------------------------------
# V2_7P 가 얀 SV(2)<->SV(3) 을 맞바꿨다. 그런데 옛 덱과 새 덱은
# *Depvar 이름 '집합'이 같고 '슬롯 번호'만 다르다:
#     새: 2=DYTT, 3=DY1C        옛: 2=DY1C, 3=DYTT
# odb 의 필드 키는 이름뿐이라(SDV_DYTT ...) 이름만으로는 구분이
# 원리적으로 불가능하다. 그래서 덱의 번호줄을 직접 읽는다.
#
# 2026-08-18: t23 덱이 '옛 이름 + 17번은 이름 있음' 조합이었다.
# patch_depvar_yarn.py 가 이름줄 있는 덱에 17번 설명을 붙이기 때문에
# 'SDV17 이 이름 없이 뜬다'는 신호로는 절대 못 잡는다 (§5.24D).
SDV_LAYOUT = ['new']


def read_yarn_sdv_layout(deck):
    """덱의 얀 *Depvar 이름줄을 읽어 'old' / 'new' / None 을 돌려준다."""
    try:
        fh = io.open(deck, encoding='utf-8', errors='replace')
    except Exception:
        return None
    try:
        lines = fh.read().splitlines()
    finally:
        fh.close()
    inyarn = False
    indv = False
    slots = {}
    for ln in lines:
        s = ln.strip()
        if s.startswith('*'):
            u = s.upper()
            if u.startswith('*MATERIAL'):
                inyarn = 'YARN' in u
                indv = False
                continue
            if inyarn and u.startswith('*DEPVAR'):
                indv = True
                continue
            if indv:
                break
            continue
        if indv and ',' in s:
            bits = [b.strip() for b in s.split(',')]
            if len(bits) >= 2 and bits[0].isdigit() and bits[1]:
                slots[int(bits[0])] = bits[1].upper()
    if slots.get(2) == 'DYTT' and slots.get(3) == 'DY1C':
        return 'new'
    if slots.get(2) == 'DY1C' and slots.get(3) == 'DYTT':
        return 'old'
    return None


def find_deck(odb_path):
    """odb 와 같은 폴더에서 얀 재료가 들어 있는 .inp 를 찾는다."""
    d = os.path.dirname(os.path.abspath(odb_path)) or '.'
    try:
        cand = sorted(f for f in os.listdir(d) if f.lower().endswith('.inp'))
    except Exception:
        return None
    for f in cand:
        p = os.path.join(d, f)
        try:
            fh = io.open(p, encoding='utf-8', errors='replace')
        except Exception:
            continue
        try:
            head = fh.read()
        finally:
            fh.close()
        if 'YARN' in head.upper() and '*DEPVAR' in head.upper():
            return p
    return None


def set_sdv_layout(odb_path, forced=None):
    """--sdv-layout 지정이 있으면 그것을, 없으면 덱에서 읽어 정한다."""
    if forced in ('old', 'new'):
        SDV_LAYOUT[0] = forced
        print('SDV layout: %s (forced by --sdv-layout)' % forced)
        return
    deck = find_deck(odb_path)
    lay = read_yarn_sdv_layout(deck) if deck else None
    if lay is None:
        SDV_LAYOUT[0] = 'new'
        print('SDV layout: new (ASSUMED -- deck not found or unreadable). '
            'If yarn transverse damage reads 0 everywhere, rerun with '
            '--sdv-layout old')
    else:
        SDV_LAYOUT[0] = lay
        print('SDV layout: %s (from %s)' % (lay, os.path.basename(deck)))
        if lay == 'old':
            print('  -> deck names slots 2/3 the pre-V2_7P way; '
                'DYTT and DY1C are read swapped')


def _stale_swap(names, nm):
    """옛 배치 덱이면 DYTT <-> DY1C 이름을 맞바꿔 진짜 슬롯을 탄다."""
    if SDV_LAYOUT[0] != 'old':
        return nm
    if nm == 'DYTT':
        return 'DY1C'
    if nm == 'DY1C':
        return 'DYTT'
    return nm


def resolve_sdv(names, nm, idx=None):
    nm = _stale_swap(names, nm)
    tgt = 'SDV_' + nm
    for n in names:
        if n == tgt:
            return n
    cand = [n for n in names if n.startswith(tgt)]
    if cand:
        cand.sort(key=len)
        return cand[0]
    # 이름 없는 덱(V2_7P + 번호 표시) 폴백
    if idx is not None:
        for n in names:
            if n == 'SDV%d' % idx:
                return n
    return None


def pick_step(odb, want):
    if want:
        st = get_set(odb.steps, want)
        if st is not None:
            return st.name
    cand = [k for k in odb.steps.keys() if k.upper().startswith('TENSION')]
    if len(cand) == 1:
        return cand[0]
    for k in odb.steps.keys():
        if 'COOL' in k.upper():
            return k
    return list(odb.steps.keys())[0]


def collect(field, elsets):
    """여러 elset 의 SDV 값을 하나의 리스트로."""
    out = []
    for es in elsets:
        try:
            vals = field.getSubset(region=es).values
        except Exception:
            continue
        for v in vals:
            out.append(_sc(v.data))
    return out


def _key(v):
    """적분점 하나를 유일하게 가리키는 키."""
    try:
        inst = v.instance.name if v.instance is not None else ''
    except AttributeError:
        inst = ''
    return (inst, v.elementLabel, v.integrationPoint)


def collect_keyed(field, elsets):
    """{(인스턴스, 요소, 적분점): 값} — 두 필드를 짝지으려면 필요하다.

    두 SDV 를 각각 flat 리스트로 뽑아 순서로 짝지으면 안 된다.
    getSubset 의 반환 순서가 필드마다 같다는 보장이 없다.
    """
    out = {}
    for es in elsets:
        try:
            vals = field.getSubset(region=es).values
        except Exception:
            continue
        for v in vals:
            out[_key(v)] = _sc(v.data)
    return out


def shear_row(r1t, shr):
    """SDV5(R1T) 와 SDV17(전단분율) 을 짝지어 개시 기구를 집계한다.

    SDV17=0 은 "σ11 단독"과 "1T 미개시" 를 둘 다 뜻하므로 반드시
    R1T>=1 로 먼저 거른다. 이 필터가 이 함수의 존재 이유다.
    """
    keys = [k for k in r1t if k in shr]
    n = len(keys)
    on = [shr[k] for k in keys if r1t[k] >= 1.0]
    if n == 0 or not on:
        return dict(n=n, n_onset=len(on), pct_onset=0.0, mean=float('nan'),
                    med=float('nan'), pct_shear=float('nan'),
                    bins=[0.0] * NBIN)
    s = sorted(on)
    bins = [0] * NBIN
    for v in on:
        i = int(v * NBIN)
        if i >= NBIN:
            i = NBIN - 1
        if i < 0:
            i = 0
        bins[i] += 1
    nshear = len([v for v in on if v > 0.5])
    return dict(
        n=n,
        n_onset=len(on),
        pct_onset=100.0 * len(on) / n,
        mean=sum(on) / len(on),
        med=s[len(s) // 2],
        pct_shear=100.0 * nshear / len(on),
        bins=[100.0 * b / len(on) for b in bins],
    )


def hist_row(vals):
    """(sum%, mean, p95, bins[NBIN]) - bins 는 전체 요소수 대비 %."""
    n = len(vals)
    if n == 0:
        return (float('nan'), float('nan'), float('nan'), [0.0] * NBIN)
    dmg = sorted(v for v in vals if v > DTH)
    bins = [0] * NBIN
    for v in dmg:
        i = int(v * NBIN)
        if i >= NBIN:
            i = NBIN - 1
        if i < 0:
            i = 0
        bins[i] += 1
    s = 100.0 * len(dmg) / n
    mean = sum(dmg) / len(dmg) if dmg else 0.0
    p95 = dmg[int(0.95 * (len(dmg) - 1))] if dmg else 0.0
    return (s, mean, p95, [100.0 * b / n for b in bins])


def check_odb_path(path):
    """odb 를 열기 전에 존재를 확인하고, 없으면 어디에 있는지 알려준다.

    폴더를 헷갈려 다른 디렉터리에서 돌리는 실수가 잦다. 트레이스백
    대신 "이 폴더의 odb" 와 "상위 트리의 odb" 를 찍어 준다.
    """
    if os.path.exists(path):
        return True
    d = os.path.dirname(os.path.abspath(path)) or '.'
    print('[error] 파일이 없다: %s' % path)
    here = sorted(glob.glob(os.path.join(d, '*.odb')))
    if here:
        print('        이 폴더의 odb: %s'
            % ', '.join(os.path.basename(p) for p in here))
    else:
        print('        이 폴더에 odb 가 없다: %s' % d)
    sib = sorted(glob.glob(os.path.join(os.path.dirname(d), '*', '*.odb')))
    if sib:
        print('        상위 트리에서 찾은 odb:')
        for p in sib[:20]:
            print('          %s' % p)
    print('        맞는 폴더로 cd 한 뒤 다시 실행할 것.')
    return False


def main():
    args = sys.argv[1:]
    tag = ''
    if '--tag' in args:
        i = args.index('--tag')
        if i + 1 < len(args):
            tag = args[i + 1]
    fr_arg = None
    if '--frames' in args:
        i = args.index('--frames')
        if i + 1 < len(args):
            fr_arg = args[i + 1]
    want_step = None
    if '--step' in args:
        i = args.index('--step')
        if i + 1 < len(args):
            want_step = args[i + 1]
    lay_arg = None
    if '--sdv-layout' in args:
        i = args.index('--sdv-layout')
        if i + 1 < len(args):
            lay_arg = args[i + 1]
    paths = [a for a in args if a.lower().endswith('.odb')]
    if not paths:
        print('usage: abaqus python extract_damage_histogram.py <job>.odb '
              '[--step NAME] [--frames a,b,c] [--tag NAME] '
              '[--sdv-layout auto|old|new]')
        return 1
    path = paths[0]
    outdir = os.path.dirname(os.path.abspath(path)) or '.'
    set_sdv_layout(path, lay_arg)

    print('opening %s ...' % path)
    if not check_odb_path(path):
        return 2
    odb = openOdb(path=path, readOnly=True)
    try:
        sname = pick_step(odb, want_step)
        st = odb.steps[sname]
        nfr = len(st.frames)
        print('step  : %s  (%d frames)' % (sname, nfr))
        if nfr == 0:
            print('[error] step has no frames')
            return 2
        if fr_arg:
            frames = [int(x) for x in fr_arg.split(',') if x.strip() != '']
        else:
            frames = [nfr - 1]
        frames = [f for f in frames if 0 <= f < nfr]
        print('frames: %s' % frames)

        smat = get_elset(odb, 'MATRIX')
        swarp = [get_elset(odb, p) for p in WARP]
        sweft = [get_elset(odb, p) for p in WEFT]
        if smat is None or None in swarp or None in sweft:
            print('[error] element sets MATRIX/YARN0..3 not all found')
            return 2

        groups = ['Matrix', 'Warp_Long', 'Warp_Trans',
                  'Weft_Long', 'Weft_Trans']

        for fi in frames:
            fr = st.frames[fi]
            names = list(fr.fieldOutputs.keys())
            f_dmt = resolve_sdv(names, 'DMT', 14)   # V2_7P: 14 = DMT 미러
            f_dy1 = resolve_sdv(names, 'DY1T', 1)
            f_dyt = resolve_sdv(names, 'DYTT', 2)
            if f_dmt is None or f_dy1 is None or f_dyt is None:
                print('  frame %d: SDV_DMT/DY1T/DYTT not found - skip' % fi)
                continue
            FD = fr.fieldOutputs
            data = {
                'Matrix': collect(FD[f_dmt], [smat]),
                'Warp_Long': collect(FD[f_dy1], swarp),
                'Warp_Trans': collect(FD[f_dyt], swarp),
                'Weft_Long': collect(FD[f_dy1], sweft),
                'Weft_Trans': collect(FD[f_dyt], sweft),
            }
            rows = dict((g, hist_row(data[g])) for g in groups)

            print('')
            print('  frame %d  (step time %.4f)' % (fi, fr.frameValue))
            print('  %-12s %8s %8s %8s   (paper Fig.A sums: see header)'
                  % ('group', 'sum%', 'mean d', 'p95 d'))
            for g in groups:
                s, m, p, _ = rows[g]
                print('  %-12s %8.2f %8.3f %8.3f' % (g, s, m, p))

            out = os.path.join(outdir,
                               'damage_hist%s_f%02d.csv' % (tag, fi))
            f = csv_open(out)
            try:
                w = csv.writer(f)
                w.writerow(['BinLo', 'BinHi'] + groups)
                for b in range(NBIN):
                    w.writerow(['%.2f' % (b / float(NBIN)),
                                '%.2f' % ((b + 1) / float(NBIN))]
                               + ['%.4f' % rows[g][3][b] for g in groups])
                w.writerow([])
                w.writerow(['sum_pct', ''] + ['%.2f' % rows[g][0]
                                              for g in groups])
                w.writerow(['mean_d', ''] + ['%.4f' % rows[g][1]
                                             for g in groups])
                w.writerow(['p95_d', ''] + ['%.4f' % rows[g][2]
                                            for g in groups])
            finally:
                f.close()
            print('  wrote %s' % out)

            # ---- V2_7D 진단: 얀 1T 개시 기구 (σ11 인가 전단인가) ----
            f_r1t = resolve_sdv(names, 'RY1T', 5)
            f_shr = resolve_sdv(names, 'YSHR1T', 17)
            if f_shr is None or f_r1t is None:
                print('  (SDV17 없음 - V2_7D 이전 odb. 전단분율 생략)')
                continue
            sets = [('Warp', swarp), ('Weft', sweft)]
            res = {}
            for gname, es in sets:
                res[gname] = shear_row(collect_keyed(FD[f_r1t], es),
                                       collect_keyed(FD[f_shr], es))
            print('')
            print('  얀 종방향 인장 개시 기구  (SDV5>=1 로 거른 것만)')
            print('  %-6s %8s %8s %8s %8s %9s'
                  % ('group', 'onset%', 'mean', 'median', 'shear%',
                     'n_onset'))
            for gname, _ in sets:
                r = res[gname]
                print('  %-6s %8.2f %8.4f %8.4f %8.2f %9d'
                      % (gname, r['pct_onset'], r['mean'], r['med'],
                         r['pct_shear'], r['n_onset']))
            print('  mean 0 에 가까우면 s11 주도, 1 에 가까우면 전단 주도.')
            print('  shear%% = 개시 요소 중 전단분율>0.5 인 비율.')

            outs = os.path.join(outdir,
                                'yarn_shear_frac%s_f%02d.csv' % (tag, fi))
            f = csv_open(outs)
            try:
                w = csv.writer(f)
                w.writerow(['BinLo', 'BinHi'] + [g for g, _ in sets])
                for b in range(NBIN):
                    w.writerow(['%.2f' % (b / float(NBIN)),
                                '%.2f' % ((b + 1) / float(NBIN))]
                               + ['%.4f' % res[g]['bins'][b]
                                  for g, _ in sets])
                w.writerow([])
                for k, lab in (('pct_onset', 'onset_pct'),
                               ('mean', 'mean_shear_frac'),
                               ('med', 'median_shear_frac'),
                               ('pct_shear', 'pct_shear_driven'),
                               ('n_onset', 'n_onset')):
                    w.writerow([lab, ''] + ['%.4f' % res[g][k]
                                            for g, _ in sets])
            finally:
                f.close()
            print('  wrote %s' % outs)
    finally:
        odb.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
