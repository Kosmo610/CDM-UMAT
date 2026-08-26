#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P4 배치 폴더를 만들고 덱을 P3 에서 복사한 뒤, 변수 하나만 바꾼다.

    python setup_p4.py            # 확인 + 복사 + 미리보기 (안 고침)
    python setup_p4.py --apply    # 위 + 실제로 한 곳 수정
    python setup_p4.py --selftest # 합성 트리로 전 과정 자체시험

바뀌는 곳은 딱 하나다.

    얀 PROPS(18)  A1T:  2.0 -> 50.0   (종방향 인장 연화지수)

왜 50 인가: V2_6 크랙밴드가 논문 XT(2835)에서 주는 값이 정확히
이것이다. g0 = XT^2/(2*E1) = 15.76, g0*le 가 이 메쉬의 모든 요소에서
GF1T(0.03962) 를 넘어 A1TEFF 는 전 요소 클램프 50 이 된다. 즉 P4 는
"크랙밴드가 켜져 있었다면 나왔을 연화"를 슬롯 하나로 재현하는
배치다. XT(2835) / Depvar(17) / 메쉬 / span / eta 는 P3 그대로다.

P3 와 달리 *Depvar 는 안 건드린다 — 이미 17 이다. 대신 17 이
아니면 멈춘다 (P3 덱이 아니라는 뜻이다).

배치 파일(.bat) 대신 파이썬인 이유: cmd 의 인코딩·괄호·따옴표 규칙은
리눅스에서 검증할 수 없다. 파이썬이면 --selftest 로 전 과정을 미리
돌려볼 수 있고, 실제로 그렇게 한다.
"""

from __future__ import print_function
import argparse
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import patch_depvar_yarn as DEPVAR          # noqa: E402
import patch_material_prop as PROP          # noqa: E402

ORI = 'CSIC_PLAIN_WEAVE_RVE_DAMAGE_V2_2.ori'
UMAT = 'UMAT_CSIC_RVE_DAMAGE_V2_7D.for'

# (P3 폴더, P3 덱, P4 폴더, P4 덱, job)
RUNS = [
    ('Try_P3', 'CSIC_PLAIN_WEAVE_RVE_23C_P3.inp',
     'Try_P4', 'CSIC_PLAIN_WEAVE_RVE_23C_P4.inp', 'CSIC_t23_p4'),
    ('Try_P3T500', 'CSIC_PLAIN_WEAVE_RVE_500C_P3.inp',
     'Try_P4T500', 'CSIC_PLAIN_WEAVE_RVE_500C_P4.inp', 'CSIC_t500_p4'),
    ('Try_P3T1000', 'CSIC_PLAIN_WEAVE_RVE_1000C_P3.inp',
     'Try_P4T1000', 'CSIC_PLAIN_WEAVE_RVE_1000C_P4.inp', 'CSIC_t1000_p4'),
]

A_SLOT = 18
A_FROM = '2.0'
A_TO = '50.0'
XT_SLOT = 11
XT_WANT = '2835.0'      # P3 계보 확인용 -- 이게 아니면 P3 덱이 아니다
GF_SLOT = 32            # 있으면 크랙밴드가 A1T 를 무시한다 -- 반드시 없어야

# *Step 서술줄에 찍을 라벨. 해석에 안 들어가는 화면 표시용이지만,
# P2 문구("XT=421 MPa, eta=0.5x")가 복사로 딸려와 P4 컨투어가 XT=421
# 로 돈 것처럼 보이는 사고가 실제로 났다 (§5.31A). ASCII 만 쓴다.
STEP_LABEL = 'P4: XT=2835 MPa, A1T=50.0, Depvar=17, UMAT V2_7D'


def head(t):
    print('')
    print('=' * 68)
    print(t)
    print('=' * 68)


def check_inputs(root):
    """없는 것을 전부 모아 한 번에 보고한다. 하나씩 죽지 않게."""
    missing = []
    need = []
    for p3d, p3f, _, _, _ in RUNS:
        need.append(os.path.join(root, p3d, p3f))
        need.append(os.path.join(root, p3d, ORI))
        need.append(os.path.join(root, p3d, UMAT))
    for p in need:
        if os.path.isfile(p):
            print('  OK     %s' % os.path.relpath(p, root))
        else:
            print('  없음   %s' % os.path.relpath(p, root))
            missing.append(p)
    return missing


def make_tree(root, force):
    """폴더를 만들고 덱/.ori/UMAT 을 P3 폴더에서 복사한다."""
    made = []
    for p3d, p3f, p4d, p4f, _ in RUNS:
        d = os.path.join(root, p4d)
        if not os.path.isdir(d):
            os.makedirs(d)
            print('  만듦   %s' % p4d)
        src_dir = os.path.join(root, p3d)
        for src, dst in (
                (os.path.join(src_dir, p3f), os.path.join(d, p4f)),
                (os.path.join(src_dir, ORI), os.path.join(d, ORI)),
                (os.path.join(src_dir, UMAT), os.path.join(d, UMAT))):
            if os.path.isfile(dst) and not force:
                print('  있음   %s  (그대로 둠. 덮으려면 --force)'
                      % os.path.relpath(dst, root))
                continue
            shutil.copyfile(src, dst)
            print('  복사   %s' % os.path.relpath(dst, root))
        made.append(os.path.join(d, p4f))
    return made


def show(decks, slot, label):
    print('  [%s]' % label)
    PROP.main([d for d in decks] + ['--material', 'YARN',
                                    '--slot', str(slot), '--show'])


def read_slot(path, want, slot):
    """덱에서 슬롯 값을 문자열로 읽는다. 못 읽으면 None."""
    lines = PROP.read_lines(path)
    for um_line, name in PROP.find_usermat(lines, want):
        dls = PROP.data_lines(lines, um_line)
        _, _, val = PROP.locate(lines, dls, slot)
        if val is not None:
            return val
    return None


def yarn_depvar_count(path):
    """얀 *Depvar 카운트. 못 읽으면 None."""
    lines = DEPVAR.read_lines(path)
    hits = DEPVAR.find_yarn_depvars(lines)
    if not hits:
        return None
    dv_line, _ = hits[0]
    a, b = DEPVAR.block_extent(lines, dv_line)
    for k in range(a, b):
        m = DEPVAR.COUNTLINE.match(lines[k].rstrip('\r\n'))
        if m:
            return int(m.group(2))
    return None


def slot_state(decks, slot, v_from, v_to):
    """세 덱의 슬롯 값이 어디에 있는지. ('from'|'to'|'mixed', 값목록).

    --apply 를 두 번 돌리면 --expect 가 안 맞아 실패한다. 덱은 이미
    옳은데 실패로 보이는 것은 나쁘다. 섞인 상태(일부만 적용)는 가장
    위험하므로 따로 갈라 멈춘다."""
    vals = [read_slot(d, 'YARN', slot) for d in decks]

    def same(x):
        try:
            return all(v is not None and abs(float(v) - float(x)) < 1e-12
                       for v in vals)
        except ValueError:
            return all(v == x for v in vals)
    if same(v_to):
        return 'to', vals
    if same(v_from):
        return 'from', vals
    return 'mixed', vals


def _quiet_call(fn, *a):
    """출력을 삼키고 (반환값, 출력) 을 돌려준다."""
    buf = io.StringIO() if str is not bytes else io.BytesIO()
    keep, sys.stdout = sys.stdout, buf
    try:
        rc = fn(*a)
    finally:
        sys.stdout = keep
    return rc, buf.getvalue()


def preflight():
    """덱을 건드리기 전에 도구들이 멀쩡한지 확인한다."""
    tools = [('setup_p4', selftest),
             ('patch_depvar_yarn', DEPVAR.selftest),
             ('patch_material_prop', PROP.selftest)]
    bad = []
    for name, fn in tools:
        rc, out = _quiet_call(fn)
        if rc:
            bad.append((name, out))
    if bad:
        print('[중단] 도구 자체시험 실패 — 덱은 건드리지 않았다.')
        for name, out in bad:
            print('')
            print('--- %s ---' % name)
            print(out[-2000:])
        print('')
        print('이 화면을 그대로 보내주십시오.')
        return 1
    print('도구 자체시험 통과 (setup_p4 / patch_depvar_yarn / '
          'patch_material_prop)')
    return 0


def lineage_ok(decks):
    """P3 계보 확인 -- XT=2835, Depvar=17, 그리고 GF1T 가 꺼져 있어야.

    GF1T 가 살아 있으면 UMAT 이 A1TEFF 를 크랙밴드로 계산하고
    PROPS(18) 을 **통째로 무시한다** (V2_7D 370-380행). 그 상태로
    A1T 를 바꾸면 아무 일도 안 일어나는 헛배치가 되므로 여기서
    막는다. 이 배치의 존재 이유가 걸린 가드다.
    """
    bad = []
    for d in decks:
        xt = read_slot(d, 'YARN', XT_SLOT)
        dv = yarn_depvar_count(d)
        gf = read_slot(d, 'YARN', GF_SLOT)
        okx = xt is not None and abs(float(xt) - float(XT_WANT)) < 1e-9
        okd = dv == 17
        okg = (gf is None) or (abs(float(gf)) <= 0.0)
        mark = 'OK  ' if (okx and okd and okg) else '문제'
        print('  %s   %-40s XT=%-8s Depvar=%-4s GF1T=%s'
              % (mark, os.path.basename(d), xt, dv,
                 '없음(정상)' if gf is None else gf))
        if not (okx and okd and okg):
            bad.append((d, okx, okd, okg))
    if bad:
        print('')
        if any(not g for _, _, _, g in bad):
            print('[중단] 얀 카드에 GF1T(슬롯 32)가 살아 있다.')
            print('       GF1T>0 이면 UMAT 이 A1TEFF 를 크랙밴드로')
            print('       계산하고 PROPS(18) 을 무시한다. A1T 를 바꿔도')
            print('       결과가 안 변하는 헛배치가 되므로 막는다.')
            print('       P3 덱은 상수 31개(슬롯 32 없음)여야 한다.')
        else:
            print('[중단] 위 덱은 P3 덱이 아니다 (XT 2835 + Depvar 17 이어야')
            print('       한다). Try_P3* 에 setup_p3 결과물이 있는지 확인.')
        return False
    return True


def fix_names(decks):
    """얀 *Depvar 이름줄이 옛 배치면 V2_7P 배치로 바로잡는다.

    이름줄은 출력 라벨일 뿐 해석에 안 들어간다 (UMAT 은 STATEV 를
    번호로 받는다). 그래서 '변수 하나' 규칙을 안 깨면서, P3 t23 을
    괴롭힌 SDV_DYTT<->SDV_DY1C 오독(§5.24D)을 P4 에서는 원천 차단할
    수 있다. 추출할 때 --sdv-layout 을 신경 쓸 필요가 없어진다.
    """
    n = 0
    for d in decks:
        lines = DEPVAR.read_lines(d)
        hits = DEPVAR.find_yarn_depvars(lines)
        if not hits:
            continue
        dv_line, _ = hits[0]
        a, b = DEPVAR.block_extent(lines, dv_line)
        data = [k for k in range(a, b) if lines[k].strip()]
        named = [k for k in data[1:] if ',' in lines[k]]
        if not named:
            print('  %-40s 이름줄 없음 -- 번호로 잡힌다 (그대로)'
                  % os.path.basename(d))
            continue
        msg = DEPVAR.fix_slot23(lines, named)
        if msg:
            if not os.path.isfile(d + '.bak'):
                shutil.copyfile(d, d + '.bak')
            DEPVAR.write_lines(d, lines)
            print('  %-40s 슬롯 2/3 이름을 V2_7P 배치로 정정'
                  % os.path.basename(d))
            n += 1
        else:
            print('  %-40s 이름배치 이미 정상' % os.path.basename(d))
    return n


def stamp_labels(decks, label):
    """덱의 *Step 서술줄을 이 배치 이름으로 새로 찍는다.

    해석에 안 들어간다 -- Abaqus 뷰포트 라벨일 뿐이다. 이미 돌린
    결과는 바뀌지 않고 재실행도 필요 없다. 다음에 컨투어를 열었을 때
    어느 카드로 돈 것인지 화면이 스스로 말하게 하는 것이 목적이다.
    """
    n = 0
    for d in decks:
        lines = PROP.read_lines(d)
        k = PROP.stamp_step_label(lines, label)
        if k:
            if not os.path.isfile(d + '.bak'):
                shutil.copyfile(d, d + '.bak')
            PROP.write_lines(d, lines)
            n += k
        print('  %-46s 스텝 라벨 %d 개' % (os.path.basename(d), k))
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description='P4 배치 준비')
    ap.add_argument('--root', default='.', help='E:\\LTH (기본: 현재 폴더)')
    ap.add_argument('--apply', action='store_true',
                    help='덱을 실제로 고친다 (없으면 미리보기)')
    ap.add_argument('--force', action='store_true',
                    help='이미 있는 P4 파일도 P3 에서 다시 복사')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--skip-selftest', action='store_true',
                    help='시작할 때 자동으로 도는 자체시험을 건너뛴다')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.skip_selftest:
        rc = preflight()
        if rc:
            return rc

    root = os.path.abspath(args.root)
    head('0) 있어야 할 것 (전부 P3 폴더에서 온다)')
    missing = check_inputs(root)
    if missing:
        print('')
        print('[중단] 위의 "없음" 을 먼저 해결할 것.')
        print('  - P3 배치(Try_P3 / Try_P3T500 / Try_P3T1000)가 끝나 있는가')
        return 1

    head('1) 폴더와 파일')
    decks = make_tree(root, args.force)

    head('2) P3 계보 확인')
    if not lineage_ok(decks):
        return 1

    head('3) 지금 상태')
    show(decks, A_SLOT, 'A1T (슬롯 18) — 세 줄 모두 %s 여야 한다' % A_FROM)
    print('')
    print('  주의: 슬롯 19/20/21 (A1C/ATT/ATC) 도 2.0 인데 그것들은')
    print('  안 건드린다. 바꾸는 것은 슬롯 18 하나다.')

    if not args.apply:
        head('4) 미리보기 — 아무것도 안 바뀌었다')
        PROP.main(decks + ['--material', 'YARN', '--slot', str(A_SLOT),
                           '--value', A_TO, '--expect', A_FROM])
        print('')
        print('확인할 것')
        print('  - 치환 대상이 CSIC_YARN_DAMAGE 뿐인가 (기지가 나오면 중단)')
        print('  - 슬롯 18 이 세 줄 모두 %s 인가' % A_FROM)
        print('')
        print('다 맞으면:  python setup_p4.py --apply')
        return 0

    head('4) 얀 SDV 이름배치 정정 (해석엔 영향 없음, 추출 사고 예방)')
    fix_names(decks)
    print('')
    print('  스텝 라벨을 이 배치 이름으로 다시 찍는다 (화면 표시용):')
    print('    %s' % STEP_LABEL)
    stamp_labels(decks, STEP_LABEL)

    head('5) 적용 — 얀 A1T %s -> %s' % (A_FROM, A_TO))
    state, vals = slot_state(decks, A_SLOT, A_FROM, A_TO)
    if state == 'to':
        print('       세 덱 모두 이미 %s. 건너뛴다 (멱등).' % A_TO)
    elif state == 'mixed':
        print('[중단] 덱마다 A1T 가 다르다 — 일부만 적용된 상태다.')
        for d, v in zip(decks, vals):
            print('       %-46s %s' % (os.path.basename(d), v))
        print('       .bak 으로 되돌리거나 --force 로 P3 에서 다시 복사할 것.')
        return 1
    else:
        rc = PROP.main(decks + ['--material', 'YARN', '--slot', str(A_SLOT),
                                '--value', A_TO, '--expect', A_FROM,
                                '--apply'])
        if rc:
            print('[중단] A1T 치환 실패 — 값이 %s 가 아니었을 수 있다'
                  % A_FROM)
            return 1

    head('6) 발사 전 최종 확인')
    show(decks, A_SLOT, 'A1T — 세 줄 모두 %s' % A_TO)
    print('')
    show(decks, XT_SLOT, 'XT — 그대로 %s 여야 한다' % XT_WANT)
    print('')
    for s, nm, wv in ((19, 'A1C', '2.0'), (20, 'ATT', '2.0'),
                      (21, 'ATC', '2.0')):
        vv = [read_slot(d, 'YARN', s) for d in decks]
        ok = all(v is not None and abs(float(v) - float(wv)) < 1e-12
                 for v in vv)
        print('  %s  슬롯 %d (%s) = %s  (그대로여야 한다)'
              % ('OK  ' if ok else '문제', s, nm,
                 vv[0] if vv else '?'))
        if not ok:
            print('[중단] 이웃 슬롯이 바뀌었다. .bak 으로 되돌릴 것.')
            return 1

    head('7) 발사 (창 3개, 10코어씩 = 30/32)')
    for _, _, p4d, p4f, job in RUNS:
        print('')
        print('  cd /d %s' % os.path.join(root, p4d))
        print('  abaqus job=%s input=%s ^' % (job, p4f))
        print('         user=%s cpus=10 int' % UMAT)
    print('')
    print('A=50 은 연화가 P3 보다 훨씬 급해 컷백이 늘 수 있다. 30분 뒤')
    print('.sta 에서 냉각이 정상 진행하는지 볼 것. 냉각은 A1T 와 거의')
    print('무관하므로 P3 와 같은 속도여야 한다.')
    return 0


# ---------------------------------------------------------------------------
def _deck(named):
    """P3 상태의 합성 덱. named=True 면 t23 계보(옛 이름 + 17 설명줄)."""
    rows = []
    if named:
        rows = ['1, DY1T, Yarn longitudinal tensile damage',
                '2, DY1C, Yarn longitudinal compressive damage',
                '3, DYTT, Yarn transverse tensile damage',
                '4, DYTC, Yarn transverse compressive damage',
                '17, YSHR1T, Shear share of longitudinal tensile criterion']
    body = ['*Material, Name=SIC_MATRIX_DAMAGE',
            '*Depvar',
            '14,']
    if named:
        body.append('1, DMT, Matrix tensile damage')
    body += ['*User Material, constants=24',
             '2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99',
             '0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031',
             '250.0, 100000.0, 1.15, 0.75, 0.50, 30.0, 0.0, 1.0',
             '*Material, Name=CSIC_YARN_DAMAGE',
             '*Depvar',
             '17,']
    body += rows
    body += ['*User Material, constants=31',
             '1.0, 254967.228042, 44321.7, 44321.7, 0.2475, 0.2475,'
             ' 0.3958, 26431.5',
             '26431.5, 15876.6, 2835.0, 1956.0, 50.0, 350.0, 120.0, 120.0',
             '100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02',
             '0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50']
    # 실제 덱처럼 스텝을 붙인다. 서술줄이 P2 문구인 것까지 그대로
    # 재현해야 stamp_labels 가 정말 갈아치우는지 시험할 수 있다.
    # (붙이기 전에는 합성 덱에 *Step 이 없어 도장이 무시험이었다.)
    body += ['*Step, name=Cooling, nlgeom=YES, inc=16000',
             'STAGE9 1000C: XT=421 MPa, eta=0.5x, V2_4 criterion',
             '*Static',
             '0.001, 1.0, 1e-08, 0.01',
             '*End Step',
             '*Step, name=Tension, nlgeom=YES, inc=16000',
             'STAGE9 1000C: XT=421 MPa, eta=0.5x, V2_4 criterion',
             '*Static',
             '0.001, 2.0, 1e-08, 0.01',
             '*End Step']
    return '\r\n'.join(body) + '\r\n'


def _slotval(body, slot):
    """합성 덱 본문에서 얀 카드 슬롯 값을 위치로 읽는다.

    상수 개수(31/38)를 가리지 않게 얀 재료 뒤의 첫 *User Material
    부터 센다."""
    tail = body.split('CSIC_YARN_DAMAGE')[1].split('*User Material')[1]
    nums = []
    for ln in tail.split('\r\n')[1:]:
        if not ln.strip() or ln.startswith('*'):
            break
        nums += [b.strip() for b in ln.split(',') if b.strip()]
    return nums[slot - 1] if len(nums) >= slot else None


def selftest():
    """합성 트리로 확인+복사+미리보기+적용 전 과정을 두 덱 모양에 돌린다."""
    import tempfile
    fails = []

    def check(tag, cond, extra=''):
        print('  %-34s %s' % (tag, 'PASS' if cond else 'FAIL'))
        if not cond:
            fails.append(tag)
            if extra:
                print(extra[-1500:])

    def quiet(argv):
        # --skip-selftest 필수. 안 그러면 main() 이 preflight() 를
        # 부르고 preflight() 가 다시 selftest() 를 불러 무한재귀가 된다.
        return _quiet_call(main, argv + ['--skip-selftest'])

    print('자체시험')
    for shape, named in [('named-stale(t23계보)', True),
                         ('nameless(500/1000계보)', False)]:
        print('  --- 덱 모양 %s ---' % shape)
        deck = _deck(named)
        tmp = tempfile.mkdtemp()

        def c(tag, cond, extra=''):
            check('%s %s' % ('N' if named else 'U', tag), cond, extra)

        for p3d, p3f, _, _, _ in RUNS:
            os.makedirs(os.path.join(tmp, p3d))
            with io.open(os.path.join(tmp, p3d, p3f), 'w',
                         encoding='utf-8', newline='') as fh:
                fh.write(deck)
            with io.open(os.path.join(tmp, p3d, ORI), 'w') as fh:
                fh.write('mesh placeholder')
            with io.open(os.path.join(tmp, p3d, UMAT), 'w') as fh:
                fh.write('      SUBROUTINE UMAT\n')

        rc, out = quiet(['--root', tmp])
        d23 = os.path.join(tmp, 'Try_P4', 'CSIC_PLAIN_WEAVE_RVE_23C_P4.inp')
        c('preview-rc0', rc == 0, out)
        c('preview-copies-deck', os.path.isfile(d23), out)
        c('preview-copies-ori',
          os.path.isfile(os.path.join(tmp, 'Try_P4', ORI)), out)
        c('preview-copies-umat',
          os.path.isfile(os.path.join(tmp, 'Try_P4', UMAT)), out)
        with io.open(d23, encoding='utf-8', newline='') as fh:
            body = fh.read()
        c('preview-writes-nothing', _slotval(body, A_SLOT) == '2.0', out)

        rc, out = quiet(['--root', tmp, '--apply'])
        with io.open(d23, encoding='utf-8', newline='') as fh:
            body = fh.read()
        c('apply-rc0', rc == 0, out)
        c('apply-a1t-50', _slotval(body, 18) == '50.0', out)
        c('apply-a1c-untouched', _slotval(body, 19) == '2.0', out)
        c('apply-att-untouched', _slotval(body, 20) == '2.0', out)
        c('apply-atc-untouched', _slotval(body, 21) == '2.0', out)
        c('apply-xt-untouched', _slotval(body, 11) == '2835.0', out)
        c('apply-xc13-untouched', _slotval(body, 13) == '50.0', out)
        c('apply-keeps-crlf', '\r\n' in body and '\n\n' not in body, out)
        c('apply-depvar-17-kept', '\r\n17,\r\n' in body, out)
        if named:
            # 이름배치는 이제 '정정되는 것' 이 정상이다 (§5.24D 재발
            # 방지). 해석엔 안 들어가므로 단일변수 규칙과 무관하다.
            c('apply-names-repaired', '2, DYTT,' in body
              and '3, DY1C,' in body and '2, DY1C,' not in body, out)
            c('apply-slot17-name-kept', '17, YSHR1T,' in body, out)
        # 스텝 라벨: P2 문구가 사라지고 P4 라벨이 두 스텝 모두에
        # 찍혀야 한다. 해석 데이터줄은 그대로여야 한다. (§5.31A)
        c('apply-steplabel-stamped', body.count(STEP_LABEL) == 2, out)
        c('apply-steplabel-old-gone', 'XT=421 MPa' not in body, out)
        c('apply-steplabel-keeps-static', body.count('*Static') == 2, out)
        c('apply-steplabel-keeps-data',
          '0.001, 1.0, 1e-08, 0.01' in body
          and '0.001, 2.0, 1e-08, 0.01' in body, out)
        c('apply-steplabel-keeps-endstep', body.count('*End Step') == 2, out)
        c('apply-leaves-bak', os.path.isfile(d23 + '.bak'), out)
        c('apply-prints-launch', 'abaqus job=CSIC_t23_p4' in out, out)

        rc, out = quiet(['--root', tmp, '--apply'])
        c('apply-twice-idempotent', rc == 0 and '이미' in out, out)
        with io.open(d23, encoding='utf-8', newline='') as fh:
            again = fh.read()
        c('apply-twice-no-change', again == body, out)

        # 일부만 적용된 상태 -- 반드시 멈춰야 한다.
        d500 = os.path.join(tmp, 'Try_P4T500',
                            'CSIC_PLAIN_WEAVE_RVE_500C_P4.inp')
        with io.open(d500, encoding='utf-8', newline='') as fh:
            keep500 = fh.read()
        with io.open(d500, 'w', encoding='utf-8', newline='') as fh:
            fh.write(keep500.replace(
                '100.0, 50.0, 2.0, 2.0', '100.0, 2.0, 2.0, 2.0'))
        rc, out = quiet(['--root', tmp, '--apply'])
        c('mixed-state-refused', rc == 1 and '일부만 적용' in out, out)
        with io.open(d500, 'w', encoding='utf-8', newline='') as fh:
            fh.write(keep500)

        # P3 원본은 절대 안 변해야 한다
        with io.open(os.path.join(tmp, 'Try_P3',
                                  'CSIC_PLAIN_WEAVE_RVE_23C_P3.inp'),
                     encoding='utf-8', newline='') as fh:
            p3 = fh.read()
        c('p3-source-untouched', _slotval(p3, 18) == '2.0'
          and _slotval(p3, 11) == '2835.0')

        shutil.rmtree(tmp)

    # 계보가 틀리면 (XT=421 = P2 덱) 복사까지만 하고 멈춰야 한다
    import tempfile as _tf
    tmp = _tf.mkdtemp()
    wrong = _deck(False).replace('26431.5, 15876.6, 2835.0',
                                 '26431.5, 15876.6, 421.0')
    for p3d, p3f, _, _, _ in RUNS:
        os.makedirs(os.path.join(tmp, p3d))
        with io.open(os.path.join(tmp, p3d, p3f), 'w',
                     encoding='utf-8', newline='') as fh:
            fh.write(wrong)
        with io.open(os.path.join(tmp, p3d, ORI), 'w') as fh:
            fh.write('m')
        with io.open(os.path.join(tmp, p3d, UMAT), 'w') as fh:
            fh.write('s')
    rc, out = _quiet_call(main, ['--root', tmp, '--apply',
                                 '--skip-selftest'])
    check('wrong-lineage-refused', rc == 1 and 'P3 덱이 아니다' in out, out)
    with io.open(os.path.join(tmp, 'Try_P4',
                              'CSIC_PLAIN_WEAVE_RVE_23C_P4.inp'),
                 encoding='utf-8', newline='') as fh:
        c4 = fh.read()
    check('wrong-lineage-no-patch', _slotval(c4, 18) == '2.0', c4)
    shutil.rmtree(tmp)

    # GF1T 가 살아 있으면(38상수 덱) 반드시 거부해야 한다.
    # A1TEFF 를 크랙밴드가 덮어써 P(18) 이 무시되기 때문이다.
    tmp = _tf.mkdtemp()
    gfdeck = _deck(False).replace(
        '0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50',
        '0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 12.5\r\n'
        '12.5, 0.0, 0.0, 700.0, 3.0, 8000.0').replace(
        'constants=31', 'constants=38')
    for p3d, p3f, _, _, _ in RUNS:
        os.makedirs(os.path.join(tmp, p3d))
        with io.open(os.path.join(tmp, p3d, p3f), 'w',
                     encoding='utf-8', newline='') as fh:
            fh.write(gfdeck)
        with io.open(os.path.join(tmp, p3d, ORI), 'w') as fh:
            fh.write('m')
        with io.open(os.path.join(tmp, p3d, UMAT), 'w') as fh:
            fh.write('s')
    rc, out = _quiet_call(main, ['--root', tmp, '--apply', '--skip-selftest'])
    check('gf1t-alive-refused', rc == 1 and 'GF1T' in out, out)
    with io.open(os.path.join(tmp, 'Try_P4',
                              'CSIC_PLAIN_WEAVE_RVE_23C_P4.inp'),
                 encoding='utf-8', newline='') as fh:
        g4 = fh.read()
    check('gf1t-alive-no-patch', _slotval(g4, 18) == '2.0', g4)
    shutil.rmtree(tmp)

    # 준비물이 없으면 복사 전에 멈춰야 한다
    empty = _tf.mkdtemp()
    rc, out = _quiet_call(main, ['--root', empty, '--skip-selftest'])
    check('missing-inputs-refused',
          rc == 1 and not os.path.isdir(os.path.join(empty, 'Try_P4')), out)
    shutil.rmtree(empty)

    print('')
    if fails:
        print('자체시험 실패: %s' % ', '.join(fails))
        return 1
    print('자체시험 통과 -- 두 덱 모양(이름/무명) 전부에서 복사·미리보기·'
          '적용·멱등·계보가드·P3 보존 확인.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
