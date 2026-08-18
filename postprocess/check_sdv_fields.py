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
    def resolve(nm, idx):
        tgt = 'SDV_' + nm
        n2 = nm
        if 'SDV17' in names and any(n == tgt or n.startswith(tgt)
                                    for n in names):
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
