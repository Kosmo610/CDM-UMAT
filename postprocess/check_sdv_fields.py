# -*- coding: utf-8 -*-
"""check_sdv_fields.py  <odb>  [elset]

odb 의 첫 스텝(냉각) 마지막 프레임에서 SDV 필드의 **실제 키 이름**과
YARN0 부분집합의 avg/max 를 있는 그대로 찍는다. 추출기가 어느 필드를
잡아야 하는지, 이름이 정확일치인지 접미사가 붙었는지 눈으로 확정하는
용도다. 출력은 전부 ASCII (cp949 콘솔에서 안 깨진다).

    abaqus python check_sdv_fields.py Try_P3\CSIC_t23_p3.odb

물리 기대값 (V2_7D, 냉각 끝):
    slot2(DTT)  avg ~0.27  max ~0.9   <- 진짜 횡손상(인장분류)
    slot3(D1C)  avg ~0     max ~0     <- 냉각 |S11|/XC = 0.17 이라 0
"""
import sys
import io
import os


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


def get_set(container, name):
    try:
        return container[name]
    except Exception:
        pass
    for k in container.keys():
        if k.upper() == name.upper():
            return container[k]
    return None


def find_elset(odb, name):
    ra = odb.rootAssembly
    s = get_set(ra.elementSets, name)
    if s is not None:
        return s
    for inst in ra.instances.values():
        s = get_set(inst.elementSets, name)
        if s is not None:
            return s
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    esname = sys.argv[2] if len(sys.argv) > 2 else 'YARN0'

    from odbAccess import openOdb
    odb = openOdb(path, readOnly=True)
    st = odb.steps.values()[0]
    fr = st.frames[-1]
    es = find_elset(odb, esname)
    print('odb   : %s' % path)
    print('step  : %s   frame %d (last)   elset %s' %
          (st.name, len(st.frames) - 1, esname))
    if es is None:
        print('ERROR: elset %s not found' % esname)
        return 1

    names = list(fr.fieldOutputs.keys())
    sdv = [n for n in names if n.upper().startswith('SDV')]
    sdv.sort()
    print('SDV field keys: %d' % len(sdv))
    for n in sdv:
        try:
            vals = [v.data for v in
                    fr.fieldOutputs[n].getSubset(region=es).values]
        except Exception as e:
            print('  %-44r  <subset failed: %s>' % (n, e))
            continue
        if vals:
            avg = sum(vals) / float(len(vals))
            print('  %-44r  n=%-6d avg %.6f  max %.6f'
                  % (n, len(vals), avg, max(vals)))
        else:
            print('  %-44r  n=0' % (n,))

    # 추출기 가드가 뭘 고를지 그대로 재현해 보여준다
    lay = read_yarn_sdv_layout(find_deck(path))
    print('deck layout: %s' % (lay if lay else 'UNKNOWN (deck not found)'))

    def resolve(nm, idx):
        n2 = nm
        if lay == 'old':
            if nm == 'DYTT':
                n2 = 'DY1C'
            elif nm == 'DY1C':
                n2 = 'DYTT'
        tgt = 'SDV_' + n2
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

    print('resolver picks:')
    for nm, idx in [('DY1T', 1), ('DYTT', 2), ('DY1', 9), ('DYT', 10),
                    ('RY1T', 5), ('YSHR1T', 17)]:
        print('  %-8s -> %r' % (nm, resolve(nm, idx)))
    odb.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
