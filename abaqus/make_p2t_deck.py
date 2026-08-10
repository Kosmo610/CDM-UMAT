#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_p2t_deck.py  --  500/1000 C 경유 덱을 P2 카드로 고쳐 새 덱을 만든다

손으로 7곳을 고치면 반드시 어딘가 틀린다. 이 스크립트가 대신 한다.
**앵커를 하나라도 못 찾으면 아무것도 쓰지 않고 멈춘다.** 반쯤 고쳐진
덱이 나오는 일은 없다.

사용법 (일반 python, abaqus 불필요)
------
  python make_p2t_deck.py <원본덱> <P2덱> <출력덱> --temp 500
  python make_p2t_deck.py <원본덱> <P2덱> <출력덱> --temp 1000

  예)
  python make_p2t_deck.py ^
     "E:\\LTH\\Try_0805까지\\Try_1430\\CSIC_PLAIN_WEAVE_RVE_500C_XT421.inp" ^
     "E:\\LTH\\Try_P2\\CSIC_PLAIN_WEAVE_RVE_23C_P2.inp" ^
     "E:\\LTH\\Try_P2T500\\CSIC_PLAIN_WEAVE_RVE_500C_P2.inp" --temp 500

무엇을 고치나 (docs/BATCH_T500_T1000_P2.md 와 같은 내용)
------------
  1) 기지 WEIBM   5.1 -> 0.0                    (P17)
  2) 기지 MCRIT   constants=23 -> 24, 끝에 1.0  (P24 신설)
  3) 얀   Yt      80.0 -> 50.0                  (P13)
  4) 인장 *Static / inc=  -> **P2 덱에서 그대로 복사**
  5) 인장 드라이버 목표 -> 500: 0.0073077 / 1000: 0.0083840
  6) 승온 스텝시간 -> 1000 덱만 1.0 -> 2.05      (dT/dt 통일)
  7) *Depvar 이름 줄 삭제 (개수 숫자는 유지)     -> SDV1/SDV2/SDV14

건드리지 않는 것: FREEZESTEP, HOM 스텝, 메쉬, 그 밖의 모든 것.
"""
from __future__ import print_function
import sys
import os
import re

NEW_DRIVER = {500: '0.0073077', 1000: '0.0083840'}
HEAT_PERIOD = {500: None, 1000: '2.05'}     # None = 그대로 둔다

CHANGES = []


def note(what, ln, before, after):
    CHANGES.append((what, ln, before, after))


def die(msg):
    print('')
    print('[중단] %s' % msg)
    print('       아무 파일도 쓰지 않았다.')
    raise SystemExit(2)


def read_lines(path):
    if not os.path.exists(path):
        die('파일이 없다: %s' % path)
    f = open(path, 'rb')
    try:
        raw = f.read()
    finally:
        f.close()
    txt = raw.decode('latin-1')          # 덱은 ASCII. 깨짐 없이 왕복된다.
    return txt.replace('\r\n', '\n').split('\n')


def step_ranges(lines):
    """[(name, start, end)] -- *Step .. *End Step 구간."""
    out = []
    cur = None
    for i, l in enumerate(lines):
        s = l.strip()
        if s.lower().startswith('*step'):
            m = re.search(r'name\s*=\s*([^,]+)', s, re.I)
            cur = [(m.group(1).strip() if m else '?'), i, None]
        elif s.lower().startswith('*end step') and cur:
            cur[2] = i
            out.append(tuple(cur))
            cur = None
    return out


def find_step(steps, prefix):
    hit = [s for s in steps if s[0].upper().startswith(prefix.upper())]
    if len(hit) != 1:
        die('%s* 스텝을 %d 개 찾았다 (1개여야 한다): %s'
            % (prefix, len(hit), [s[0] for s in steps]))
    return hit[0]


def static_line_in(lines, a, b):
    """구간 안의 *Static 바로 다음 데이터 줄 index."""
    for i in range(a, b):
        if lines[i].strip().lower().startswith('*static'):
            j = i + 1
            while j < b and (not lines[j].strip()
                             or lines[j].strip().startswith('**')):
                j += 1
            if j < b and not lines[j].strip().startswith('*'):
                return j
    return None


def replace_once(lines, old, new, what):
    hits = [i for i, l in enumerate(lines) if l.strip() == old]
    if len(hits) != 1:
        die('"%s" 를 %d 번 찾았다 (1번이어야 한다) -- %s'
            % (old, len(hits), what))
    i = hits[0]
    note(what, i + 1, lines[i].strip(), new)
    lines[i] = new
    return lines


def strip_depvar_names(lines):
    """*Depvar 아래 "3, NAME, 설명" 형태의 이름 줄만 지운다.
    개수 줄("20," 등)은 남긴다."""
    out = []
    i = 0
    n = 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip().lower().startswith('*depvar'):
            i += 1
            # 개수 줄
            while i < len(lines) and (not lines[i].strip()
                                      or lines[i].strip().startswith('**')):
                out.append(lines[i])
                i += 1
            if i < len(lines):
                out.append(lines[i])          # 개수 줄 유지
                cnt = lines[i].strip()
                i += 1
            # 이름 줄: "번호, 이름, 설명"
            drop = 0
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('*') or not s:
                    break
                if re.match(r'^\d+\s*,\s*[A-Za-z_]', s):
                    drop += 1
                    i += 1
                    continue
                break
            if drop:
                # 덱은 ASCII 로만 쓴다. 한글을 넣으면 latin-1 로 못 쓰고,
                # Abaqus 가 cp949 환경에서 읽을 때도 위험하다.
                out.append('** V2_7P: depvar name lines removed -> fields'
                           ' show as SDV<n> (%s slots).'
                           ' See docs/SDV_PAPER_DISPLAY.md'
                           % cnt.rstrip(','))
                note('*Depvar 이름 줄 삭제', len(out), '%d 줄' % drop, '주석 1줄')
                n += 1
            continue
        i += 1
    if n != 2:
        die('*Depvar 이름 블록을 %d 개 처리했다 (기지+얀 = 2 개여야 한다)' % n)
    return out


def main():
    args = sys.argv[1:]
    temp = None
    if '--temp' in args:
        k = args.index('--temp')
        temp = int(args[k + 1])
        args = args[:k] + args[k + 2:]
    paths = [a for a in args if not a.startswith('-')]
    if len(paths) != 3 or temp not in NEW_DRIVER:
        print(__doc__)
        return 1
    src_p, p2_p, out_p = paths

    src = read_lines(src_p)
    p2 = read_lines(p2_p)
    print('원본 : %s  (%d 줄)' % (src_p, len(src)))
    print('P2   : %s  (%d 줄)' % (p2_p, len(p2)))
    print('출력 : %s   [%d C]' % (out_p, temp))
    print('')

    # ---- 1+2) 기지 WEIBM 5.1 -> 0.0  &  MCRIT 추가 --------------------
    src = replace_once(
        src, '5.1, 1.0, 1.15, 0.75, 0.50, 1.0, 1.0',
        '0.0, 1.0, 1.15, 0.75, 0.50, 1.0, 1.0, 1.0',
        '기지 WEIBM 5.1->0.0 + MCRIT 1.0 추가')
    src = replace_once(
        src, '*User Material, constants=23',
        '*User Material, constants=24',
        '기지 constants 23->24')

    # ---- 3) 얀 Yt 80 -> 50 -------------------------------------------
    yt_old = ('26431.515264, 15876.667974, 421.0, 1500.0,'
              ' 80.0, 350.0, 120.0, 120.0')
    yt_new = ('26431.515264, 15876.667974, 421.0, 1500.0,'
              ' 50.0, 350.0, 120.0, 120.0')
    src = replace_once(src, yt_old, yt_new, '얀 Yt 80->50')

    # ---- 4) 인장 *Static / inc= 를 P2 에서 복사 ------------------------
    p2_steps = step_ranges(p2)
    p2_ten = find_step(p2_steps, 'Tension')
    p2_stat_i = static_line_in(p2, p2_ten[1], p2_ten[2])
    if p2_stat_i is None:
        die('P2 덱의 인장 스텝에서 *Static 데이터 줄을 못 찾았다')
    p2_stat = p2[p2_stat_i].strip()
    m = re.search(r'inc\s*=\s*(\d+)', p2[p2_ten[1]], re.I)
    p2_inc = m.group(1) if m else None
    print('P2 인장 스텝: %s' % p2[p2_ten[1]].strip())
    print('P2 인장 *Static: %s' % p2_stat)
    print('')

    steps = step_ranges(src)
    ten = find_step(steps, 'Tension')
    stat_i = static_line_in(src, ten[1], ten[2])
    if stat_i is None:
        die('원본 덱의 인장 스텝에서 *Static 데이터 줄을 못 찾았다')
    note('인장 *Static (P2 에서 복사)', stat_i + 1, src[stat_i].strip(), p2_stat)
    src[stat_i] = p2_stat
    if p2_inc:
        old_hdr = src[ten[1]]
        new_hdr = re.sub(r'(inc\s*=\s*)\d+', r'\g<1>' + p2_inc, old_hdr,
                         flags=re.I)
        if new_hdr != old_hdr:
            note('인장 inc= (P2 에서 복사)', ten[1] + 1,
                 old_hdr.strip(), new_hdr.strip())
            src[ten[1]] = new_hdr

    # ---- 5) 인장 드라이버 목표 ----------------------------------------
    drv = [i for i in range(ten[1], ten[2])
           if src[i].strip().lower().startswith('constraintsdriver0,')]
    if len(drv) != 1:
        die('인장 스텝 안의 ConstraintsDriver0 줄이 %d 개다 (1개여야 한다)'
            % len(drv))
    i = drv[0]
    new = 'ConstraintsDriver0, 1, 1, %s' % NEW_DRIVER[temp]
    note('인장 드라이버 목표', i + 1, src[i].strip(), new)
    src[i] = new

    # ---- 6) 승온 스텝시간 (1000 만) -----------------------------------
    if HEAT_PERIOD[temp]:
        heat = find_step(steps, 'Heating')
        hi = static_line_in(src, heat[1], heat[2])
        if hi is None:
            die('승온 스텝에서 *Static 데이터 줄을 못 찾았다')
        parts = [x.strip() for x in src[hi].split(',')]
        if len(parts) < 2:
            die('승온 *Static 줄 형식이 예상과 다르다: %s' % src[hi])
        old = src[hi].strip()
        parts[1] = HEAT_PERIOD[temp]
        src[hi] = ', '.join(parts)
        note('승온 스텝시간 (dT/dt 통일)', hi + 1, old, src[hi])

    # ---- 7) *Depvar 이름 줄 삭제 --------------------------------------
    src = strip_depvar_names(src)

    # ---- 쓰기 ---------------------------------------------------------
    d = os.path.dirname(os.path.abspath(out_p))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    f = open(out_p, 'wb')
    try:
        f.write('\n'.join(src).encode('latin-1'))
    finally:
        f.close()

    print('=== 바뀐 곳 %d 군데 ===' % len(CHANGES))
    for what, ln, before, after in CHANGES:
        print('  [%s]  (원본 %d 줄 부근)' % (what, ln))
        print('      전: %s' % before)
        print('      후: %s' % after)
    print('')
    print('wrote %s' % out_p)
    print('')
    print('다음: fc 로 눈으로 한 번 더 확인할 것')
    print('  fc "%s" "%s"' % (src_p, out_p))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
