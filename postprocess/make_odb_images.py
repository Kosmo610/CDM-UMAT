# -*- coding: utf-8 -*-
"""
논문 Fig.3/5/7/9/12/14/16 형식의 그림 자동 생성

논문 그림은 전부 "기지만" 과 "얀만" 을 따로 그린 것이다. Abaqus 에서는
Display Group 으로 상(phase)을 갈라서 보여준다. 이 스크립트는 그 작업을
GUI 없이 자동으로 돌려 PNG 로 저장한다.

실행 (GUI 없이):
    abaqus viewer noGUI=make_odb_images.py -- <job>.odb [옵션]

옵션:
    --step NAME     기본: 냉각 Step 자동 검색
    --frames a,b,c  프레임 번호. 기본: 0,25%,50%,75%,100% 5장
    --var S11       기본 S11 (논문 Fig.3/7/9 와 동일). MISES / SDV_DMT 등도 가능
    --out DIR       기본: odb 폴더

산출:
    <out>/img_<var>_matrix_f<NN>.png
    <out>/img_<var>_yarn_f<NN>.png

논문 범례 고정값 (Fig.3/7/9 에서 읽음):
    기지 S11   -160 ~ +310 MPa
    얀   S11   -600 ~ +270 MPa
범례를 고정해야 프레임끼리 색이 비교된다. --auto 를 주면 자동 범위.

주의: 이 스크립트는 Abaqus Viewer 커널에서만 돈다 (여기서는 문법만
검증했고 실제 렌더링은 워크스테이션에서 확인해야 한다).
"""
from __future__ import print_function

import sys
import os

from abaqus import session
from abaqusConstants import (CONTOURS_ON_DEF, INTEGRATION_POINT, COMPONENT,
                             INVARIANT, OFF, ON, PNG, LARGE)
import displayGroupOdbToolset as dgo

MATRIX_SETS = ('MATRIX',)
YARN_SETS = ('YARN0', 'YARN1', 'YARN2', 'YARN3')
# 논문 Fig.3 / Fig.7 / Fig.9 범례
LIMITS = {'S11': {'matrix': (-160.0, 310.0), 'yarn': (-600.0, 270.0)}}
T0, T1 = 1050.0, 23.0


def argval(args, key, default=None):
    if key in args:
        i = args.index(key)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def full_setnames(odb, wanted):
    """odb 의 실제 elementSet 이름을 찾아준다.

    어셈블리 레벨이면 이름 그대로, 인스턴스 레벨이면 'INST.SET' 형태가
    필요하다. 대소문자도 odb 가 대문자로 저장하므로 맞춰준다.
    """
    ra = odb.rootAssembly
    out = []
    have_asm = dict((k.upper(), k) for k in ra.elementSets.keys())
    for w in wanted:
        u = w.upper()
        if u in have_asm:
            out.append(have_asm[u])
            continue
        found = None
        for iname, inst in ra.instances.items():
            have = dict((k.upper(), k) for k in inst.elementSets.keys())
            if u in have:
                found = '%s.%s' % (iname, have[u])
                break
        if found:
            out.append(found)
        else:
            print('  [warn] elementSet %s not found' % w)
    return tuple(out)


def pick_step(odb, want):
    if want and want in odb.steps:
        return want
    for k in odb.steps.keys():
        if 'COOL' in k.upper():
            return k
    return list(odb.steps.keys())[0]


def main():
    args = sys.argv[1:]
    if '--' in args:
        args = args[args.index('--') + 1:]
    paths = [a for a in args if a.lower().endswith('.odb')]
    if not paths:
        print('usage: abaqus viewer noGUI=make_odb_images.py -- <job>.odb '
              '[--step NAME] [--frames 0,25,50] [--var S11] [--out DIR]')
        return 1
    path = paths[0]
    var = argval(args, '--var', 'S11')
    outdir = argval(args, '--out') or (os.path.dirname(os.path.abspath(path))
                                       or '.')
    auto = '--auto' in args

    odb = session.openOdb(path=path, readOnly=True)
    step = pick_step(odb, argval(args, '--step'))
    nfr = len(odb.steps[step].frames)
    print('odb   : %s' % os.path.basename(path))
    print('step  : %s  (%d frames)' % (step, nfr))

    fr_arg = argval(args, '--frames')
    if fr_arg:
        frames = [int(x) for x in fr_arg.split(',')]
    else:
        frames = sorted(set(int(round(f * (nfr - 1)))
                            for f in (0.0, 0.25, 0.5, 0.75, 1.0)))
    print('frames: %s' % frames)

    groups = [('matrix', full_setnames(odb, MATRIX_SETS)),
              ('yarn', full_setnames(odb, YARN_SETS))]

    vp = session.viewports[session.viewports.keys()[0]]
    vp.setValues(displayedObject=odb)
    vp.makeCurrent()
    vp.maximize()
    vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))

    # 논문 그림처럼 등각 시점. 회전값이 마음에 안 들면 GUI 에서 맞춘 뒤
    # View > Save 로 저장한 이름을 여기에 넣으면 된다.
    try:
        vp.view.setValues(session.views['Iso'])
        vp.view.fitView()
    except Exception:
        pass

    # 변수 지정: 성분(S11)이면 COMPONENT, MISES 면 INVARIANT
    label = 'S'
    if var.upper().startswith('SDV'):
        label = var
        try:
            vp.odbDisplay.setPrimaryVariable(
                variableLabel=label, outputPosition=INTEGRATION_POINT)
        except Exception as e:
            print('  [error] variable %s: %s' % (var, e))
            return 2
    elif var.upper() == 'MISES':
        vp.odbDisplay.setPrimaryVariable(
            variableLabel='S', outputPosition=INTEGRATION_POINT,
            refinement=(INVARIANT, 'Mises'))
    else:
        vp.odbDisplay.setPrimaryVariable(
            variableLabel='S', outputPosition=INTEGRATION_POINT,
            refinement=(COMPONENT, var))

    session.printOptions.setValues(vpDecorations=OFF, reduceColors=False)
    session.pngOptions.setValues(imageSize=(1600, 1200))

    made = []
    for gname, sets in groups:
        if not sets:
            continue
        vp.odbDisplay.displayGroup.replace(
            leaf=dgo.LeafFromElementSets(elementSets=sets))
        lim = LIMITS.get(var.upper(), {}).get(gname)
        if lim and not auto:
            vp.odbDisplay.contourOptions.setValues(
                minAutoCompute=OFF, minValue=lim[0],
                maxAutoCompute=OFF, maxValue=lim[1])
        else:
            vp.odbDisplay.contourOptions.setValues(
                minAutoCompute=ON, maxAutoCompute=ON)
        for fi in frames:
            if fi >= nfr:
                continue
            vp.odbDisplay.setFrame(step=step, frame=fi)
            temp = T0 - (T0 - T1) * odb.steps[step].frames[fi].frameValue
            fn = os.path.join(outdir, 'img_%s_%s_f%02d'
                              % (var.upper(), gname, fi))
            session.printToFile(fileName=fn, format=PNG,
                                canvasObjects=(vp,))
            made.append((gname, fi, temp, fn + '.png'))
            print('  %-6s frame %3d  T~%7.1f C  -> %s.png'
                  % (gname, fi, temp, os.path.basename(fn)))

    odb.close()
    print('')
    print('wrote %d images in %s' % (len(made), outdir))
    print('paper Fig.3/5/7 style: top row = matrix, bottom row = yarns')
    return 0


if __name__ == '__main__':
    main()
