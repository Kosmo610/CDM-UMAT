#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P3 배치 폴더를 만들고 덱을 P2 에서 복사한 뒤, 변수 하나만 바꾼다.

    python setup_p3.py            # 확인 + 복사 + 미리보기 (안 고침)
    python setup_p3.py --apply    # 위 + 실제로 두 곳 수정
    python setup_p3.py --selftest # 합성 트리로 전 과정 자체시험

바뀌는 곳은 딱 둘이다.

    얀 *Depvar    16    -> 17      (진단 SDV17 자리)
    얀 PROPS(11)  421.0 -> 2835.0  (이번 배치의 유일한 변수)

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

# (P2 폴더, P2 덱, P3 폴더, P3 덱, job)
RUNS = [
    ('Try_P2', 'CSIC_PLAIN_WEAVE_RVE_23C_P2.inp',
     'Try_P3', 'CSIC_PLAIN_WEAVE_RVE_23C_P3.inp', 'CSIC_t23_p3'),
    ('Try_P2T500', 'CSIC_PLAIN_WEAVE_RVE_500C_P2.inp',
     'Try_P3T500', 'CSIC_PLAIN_WEAVE_RVE_500C_P3.inp', 'CSIC_t500_p3'),
    ('Try_P2T1000', 'CSIC_PLAIN_WEAVE_RVE_1000C_P2.inp',
     'Try_P3T1000', 'CSIC_PLAIN_WEAVE_RVE_1000C_P3.inp', 'CSIC_t1000_p3'),
]

XT_SLOT = 11
XT_FROM = '421.0'
XT_TO = '2835.0'
GF_SLOT = 32


def head(t):
    print('')
    print('=' * 68)
    print(t)
    print('=' * 68)


def check_inputs(root):
    """없는 것을 전부 모아 한 번에 보고한다. 하나씩 죽지 않게."""
    missing = []
    need = [os.path.join(root, UMAT)]
    for p2d, p2f, _, _, _ in RUNS:
        need.append(os.path.join(root, p2d, p2f))
    need.append(os.path.join(root, RUNS[0][0], ORI))
    for p in need:
        if os.path.isfile(p):
            print('  OK     %s' % os.path.relpath(p, root))
        else:
            print('  없음   %s' % os.path.relpath(p, root))
            missing.append(p)
    return missing


def make_tree(root, force):
    """폴더를 만들고 덱/.ori/UMAT 을 복사한다. 이미 있으면 두고 간다."""
    src_ori = os.path.join(root, RUNS[0][0], ORI)
    src_umat = os.path.join(root, UMAT)
    made = []
    for _, p2f, p3d, p3f, _ in RUNS:
        d = os.path.join(root, p3d)
        if not os.path.isdir(d):
            os.makedirs(d)
            print('  만듦   %s' % p3d)
        for src, dst in (
                (os.path.join(root, _p2dir(p3d), p2f), os.path.join(d, p3f)),
                (src_ori, os.path.join(d, ORI)),
                (src_umat, os.path.join(d, UMAT))):
            if os.path.isfile(dst) and not force:
                print('  있음   %s  (그대로 둠. 덮으려면 --force)'
                      % os.path.relpath(dst, root))
                continue
            shutil.copyfile(src, dst)
            print('  복사   %s' % os.path.relpath(dst, root))
        made.append(os.path.join(d, p3f))
    return made


def _p2dir(p3dir):
    for p2d, _, d, _, _ in RUNS:
        if d == p3dir:
            return p2d
    raise KeyError(p3dir)


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


def xt_state(decks):
    """세 덱의 XT 가 어디에 있는지. ('from'|'to'|'mixed', 값목록).

    --apply 를 두 번 돌리면 --expect 421.0 이 안 맞아 실패한다. 덱은
    이미 옳은데 실패로 보이는 것은 나쁘다. 그래서 적용 전에 어디에
    서 있는지 먼저 읽는다. 섞여 있는 상태(일부만 적용됨)는 가장
    위험하므로 따로 갈라 멈춘다."""
    vals = [read_slot(d, 'YARN', XT_SLOT) for d in decks]
    def same(x):
        try:
            return all(v is not None and abs(float(v) - float(x)) < 1e-12
                       for v in vals)
        except ValueError:
            return all(v == x for v in vals)
    if same(XT_TO):
        return 'to', vals
    if same(XT_FROM):
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
    """덱을 건드리기 전에 세 도구가 멀쩡한지 확인한다.

    사용자가 자체시험 명령을 따로 치게 하면 오타가 끼어들 자리가
    생긴다. 여기서 자동으로 돈다."""
    tools = [('setup_p3', selftest),
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
    print('도구 자체시험 통과 (setup_p3 / patch_depvar_yarn / '
          'patch_material_prop)')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='P3 배치 준비')
    ap.add_argument('--root', default='.', help='E:\\LTH (기본: 현재 폴더)')
    ap.add_argument('--apply', action='store_true',
                    help='덱을 실제로 고친다 (없으면 미리보기)')
    ap.add_argument('--force', action='store_true',
                    help='이미 있는 P3 파일도 P2 에서 다시 복사')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--skip-selftest', action='store_true',
                    help='시작할 때 자동으로 도는 자체시험을 건너뛴다')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    # 세 도구의 자체시험을 시작할 때 자동으로 돌린다. 사용자가 따로
    # 명령을 하나 더 치지 않아도 되고, 덱을 건드리기 전에 도구가
    # 멀쩡한지 늘 확인된다. 1 초도 안 걸린다.
    if not args.skip_selftest:
        rc = preflight()
        if rc:
            return rc

    root = os.path.abspath(args.root)
    head('0) 있어야 할 것')
    missing = check_inputs(root)
    if missing:
        print('')
        print('[중단] 위의 "없음" 을 먼저 해결할 것.')
        print('  - zip 을 %s 에 풀었는가' % root)
        print('  - P2 배치(Try_P2 / Try_P2T500 / Try_P2T1000)가 끝나 있는가')
        return 1

    head('1) 폴더와 파일')
    decks = make_tree(root, args.force)

    head('2) 지금 상태')
    show(decks, XT_SLOT, 'XT (슬롯 11) — 세 줄 모두 %s 여야 한다' % XT_FROM)
    print('')
    print('  [*Depvar — 얀 16 이어야 한다. 기지는 안 건드린다]')
    DEPVAR.main(decks + ['--check'])

    if not args.apply:
        head('3) 미리보기 — 아무것도 안 바뀌었다')
        DEPVAR.main(decks)
        print('')
        PROP.main(decks + ['--material', 'YARN', '--slot', str(XT_SLOT),
                           '--value', XT_TO, '--expect', XT_FROM])
        print('')
        print('확인할 것')
        print('  - 치환 대상이 CSIC_YARN_DAMAGE 뿐인가 (기지가 나오면 중단)')
        print('  - XT 가 세 줄 모두 %s 인가 (아니면 P2 덱이 아니다)' % XT_FROM)
        print('')
        print('다 맞으면:  python setup_p3.py --apply')
        return 0

    head('3) 적용')
    print('  [a] 얀 *Depvar 16 -> 17')
    rc = DEPVAR.main(decks + ['--apply'])
    if rc:
        print('[중단] Depvar 치환 실패')
        return 1
    print('')
    print('  [b] 얀 XT %s -> %s' % (XT_FROM, XT_TO))
    state, vals = xt_state(decks)
    if state == 'to':
        print('       세 덱 모두 이미 %s. 건너뛴다 (멱등).' % XT_TO)
    elif state == 'mixed':
        print('[중단] 덱마다 XT 가 다르다 — 일부만 적용된 상태다.')
        for d, v in zip(decks, vals):
            print('       %-46s %s' % (os.path.basename(d), v))
        print('       .bak 으로 되돌리거나 --force 로 P2 에서 다시 복사할 것.')
        return 1
    else:
        rc = PROP.main(decks + ['--material', 'YARN', '--slot', str(XT_SLOT),
                                '--value', XT_TO, '--expect', XT_FROM,
                                '--apply'])
        if rc:
            print('[중단] XT 치환 실패 — 값이 %s 가 아니었을 수 있다'
                  % XT_FROM)
            return 1

    head('4) 발사 전 최종 확인')
    show(decks, XT_SLOT, 'XT — 세 줄 모두 %s' % XT_TO)
    print('')
    show(decks, GF_SLOT, 'GF1T (슬롯 32)')
    gf = [read_slot(d, 'YARN', GF_SLOT) for d in decks]
    if all(v is None for v in gf):
        print('       -> 슬롯 32 가 없다. 얀 크랙밴드는 꺼져 있다(GF1T=0).')
        print('          A1TEFF = A1T = PROPS(18) 고정. 정상이며, 이 배치엔')
        print('          오히려 유리하다 — 크랙밴드가 켜져 있었다면 XT 를')
        print('          바꿀 때 g0=XT^2/(2E1) 을 통해 연화지수까지 같이')
        print('          움직여 "변수 하나" 가 깨진다.')
    else:
        for d, v in zip(decks, gf):
            if v is not None and abs(float(v)) > 0.5:
                print('       [경고] %s 의 GF1T=%s 는 가드 상한(0.5)을 넘는다.'
                      % (os.path.basename(d), v))
                print('              잡이 첫 증분에서 XIT 한다.')
    print('')
    print('  [*Depvar — 얀 17, 기지는 그대로]')
    DEPVAR.main(decks + ['--check'])

    head('5) 발사 (창 3개, 10코어씩 = 30/32)')
    for _, _, p3d, p3f, job in RUNS:
        print('')
        print('  cd /d %s' % os.path.join(root, p3d))
        print('  abaqus job=%s input=%s ^' % (job, p3f))
        print('         user=%s cpus=10 int' % UMAT)
    print('')
    print('발사 30분 뒤 .sta 와 .msg 를 볼 것 (RUN_ME.md 4절).')
    return 0


def _deck(matrix_depvar, yarn_constants):
    """덱 두 모양을 만든다.

    A(38/20) 는 문서가 오래 추정하던 모양, B(31/14) 는 2026-08-12 에
    사용자 PC 에서 실측한 진짜 모양이다. B 에는 슬롯 32(GF1T)가
    아예 없어 얀 크랙밴드가 꺼져 있다. 둘 다 통과해야 한다.
    """
    yarn = [
        '1.0, 254967.228042, 44321.7, 44321.7, 0.2475, 0.2475, 0.3958, 26431.5',
        '26431.5, 15876.6, 421.0, 1956.0, 50.0, 350.0, 120.0, 120.0',
        '100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02',
    ]
    if yarn_constants == 31:
        yarn.append('0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50')
    else:
        yarn.append('0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 0.03962')
        yarn.append('0.03962, 0.0, 0.0, 700.0, 3.0, 8000.0')
    return """*Material, Name=SIC_MATRIX_DAMAGE
*Depvar
%d,
*User Material, constants=24
2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99
0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031
250.0, 100000.0, 1.15, 0.75, 0.50, 30.0, 0.0, 1.0
*Material, Name=CSIC_YARN_DAMAGE
*Depvar
16,
*User Material, constants=%d
%s
""" % (matrix_depvar, yarn_constants, '\n'.join(yarn))


# (모양이름, 기지 Depvar, 얀 상수개수)
DECK_SHAPES = [
    ('B31', 14, 31),   # 실측 -- 사용자 덱이 이 모양이다
    ('A38', 20, 38),   # 문서 추정 -- 과거 덱 호환 확인용
]


def selftest():
    """합성 트리로 확인+복사+미리보기+적용 전 과정을 두 덱 모양에 돌린다."""
    import tempfile
    fails = []

    def check(tag, cond, extra=''):
        print('  %-32s %s' % (tag, 'PASS' if cond else 'FAIL'))
        if not cond:
            fails.append(tag)
            if extra:
                print(extra[-1500:])

    def quiet(argv):
        # --skip-selftest 필수. 안 그러면 main() 이 preflight() 를
        # 부르고 preflight() 가 다시 selftest() 를 불러 무한재귀가 된다.
        return _quiet_call(main, argv + ['--skip-selftest'])

    print('자체시험')
    for shape, mdep, ycon in DECK_SHAPES:
        print('  --- 덱 모양 %s (기지 Depvar %d / 얀 상수 %d) ---'
              % (shape, mdep, ycon))
        deck = _deck(mdep, ycon)
        tmp = tempfile.mkdtemp()

        def c(tag, cond, extra=''):
            check('%s %s' % (shape, tag), cond, extra)

        for p2d, p2f, _, _, _ in RUNS:
            os.makedirs(os.path.join(tmp, p2d))
            with io.open(os.path.join(tmp, p2d, p2f), 'w',
                         encoding='utf-8', newline='\r\n') as fh:
                fh.write(deck)
        with io.open(os.path.join(tmp, RUNS[0][0], ORI), 'w') as fh:
            fh.write('mesh placeholder')
        with io.open(os.path.join(tmp, UMAT), 'w') as fh:
            fh.write('      SUBROUTINE UMAT\n')

        rc, out = quiet(['--root', tmp])
        d23 = os.path.join(tmp, 'Try_P3', 'CSIC_PLAIN_WEAVE_RVE_23C_P3.inp')
        c('preview-rc0', rc == 0, out)
        c('preview-copies-tree', os.path.isfile(d23), out)
        c('preview-copies-ori',
          os.path.isfile(os.path.join(tmp, 'Try_P3', ORI)), out)
        c('preview-copies-umat',
          os.path.isfile(os.path.join(tmp, 'Try_P3', UMAT)), out)
        with io.open(d23, encoding='utf-8', newline='') as fh:
            body = fh.read()
        c('preview-writes-nothing', '421.0' in body and '16,' in body, out)

        rc, out = quiet(['--root', tmp, '--apply'])
        with io.open(d23, encoding='utf-8', newline='') as fh:
            body = fh.read()
        c('apply-rc0', rc == 0, out)
        c('apply-xt-2835', '2835.0' in body and '421.0' not in body, out)
        c('apply-depvar-17', '\r\n17,\r\n' in body, out)
        c('apply-matrix-untouched', '\r\n%d,\r\n' % mdep in body, out)
        c('apply-keeps-crlf', '\r\n' in body and '\n\n' not in body, out)
        c('apply-keeps-constants', 'constants=%d' % ycon in body, out)
        # 31 짜리엔 GF1T 가 없어야 하고, 38 짜리엔 남아 있어야 한다.
        if ycon == 31:
            c('apply-no-gf1t-slot', '0.03962' not in body, out)
        else:
            c('apply-keeps-gf1t', body.count('0.03962') == 2, out)
        c('apply-leaves-bak', os.path.isfile(d23 + '.bak'), out)
        c('apply-prints-launch', 'abaqus job=CSIC_t23_p3' in out, out)

        rc, out = quiet(['--root', tmp, '--apply'])
        c('apply-twice-idempotent', rc == 0 and '이미' in out, out)
        with io.open(d23, encoding='utf-8', newline='') as fh:
            again = fh.read()
        c('apply-twice-no-change', again == body, out)

        # 일부만 적용된 상태 -- 가장 위험하다. 반드시 멈춰야 한다.
        d500 = os.path.join(tmp, 'Try_P3T500',
                            'CSIC_PLAIN_WEAVE_RVE_500C_P3.inp')
        with io.open(d500, encoding='utf-8', newline='') as fh:
            keep500 = fh.read()
        with io.open(d500, 'w', encoding='utf-8', newline='') as fh:
            fh.write(keep500.replace('2835.0', '421.0'))
        rc, out = quiet(['--root', tmp, '--apply'])
        c('mixed-state-refused', rc == 1 and '일부만 적용' in out, out)
        with io.open(d500, 'w', encoding='utf-8', newline='') as fh:
            fh.write(keep500)

        # P2 원본은 절대 안 변해야 한다
        with io.open(os.path.join(tmp, 'Try_P2',
                                  'CSIC_PLAIN_WEAVE_RVE_23C_P2.inp'),
                     encoding='utf-8', newline='') as fh:
            p2 = fh.read()
        c('p2-source-untouched', '421.0' in p2 and '\r\n16,\r\n' in p2)

        shutil.rmtree(tmp)

    # 준비물이 없으면 복사 전에 멈춰야 한다 (덱 모양과 무관)
    empty = tempfile.mkdtemp()
    rc, out = quiet(['--root', empty])
    check('missing-inputs-refused',
          rc == 1 and not os.path.isdir(os.path.join(empty, 'Try_P3')), out)
    shutil.rmtree(empty)

    print('')
    if fails:
        print('자체시험 실패: %s' % ', '.join(fails))
        return 1
    print('자체시험 통과 -- 두 덱 모양(31/38) 전부에서 '
          '복사·미리보기·적용·멱등·P2 보존 확인.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
