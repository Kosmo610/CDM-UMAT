# -*- coding: utf-8 -*-
"""
논문 Fig.3/5/7/8/9/10 형식의 그림 자동 생성  (온도 지정 지원)

논문 그림은 전부 "기지만" 과 "얀만" 을 따로, 그리고 **정해진 온도**에서
그린 것이다:
  Fig.3/5   냉각      1050 / 750 / 500 / 250 / 23 C
  Fig.7/8   승온(500)   23 / 125 / 250 / 375 / 500 C
  Fig.9/10  승온(1000) 500 / 625 / 750 / 875 / 1000 C
Fig.3/7/9 는 S11 잔류응력, Fig.5/8/10 은 손상 3행(기지/종/횡)이다.

실행 (GUI 없이):
    abaqus cae noGUI=make_odb_images.py -- <job>.odb [옵션]
    (viewer 커널에는 displayGroupOdbToolset 이 없다. 반드시 cae)

옵션:
    --fig stress    S11 을 기지/얀으로 (논문 Fig.3/7/9). 범례 논문값 고정
    --fig damage    손상 3행: 기지 DMT / 얀 DY1T / 얀 DYTT (Fig.5/8/10).
                    범례 0~1 고정 (논문과 동일)
    --var NAME      프리셋 대신 단일 변수 (S11/MISES/SDV_DMT ...)
    --step NAME     기본: 냉각 Step 자동 검색
    --temps a,b,c   **온도[C]로 프레임 선택** (논문 방식). 예: 1050,750,500,250,23
    --trange A,B    Step 의 시작/끝 온도 수동 지정. 자동 인식:
                      *Cool*          -> 1050 -> 23
                      Heating_*500C*  -> 23 -> 500   (이름의 숫자)
                      Tension_*       -> 온도 일정 (temps 사용 불가)
                    직행(DIRECT) 덱의 냉각은 1050->500/1000 이므로
                    반드시 --trange 1050,500 처럼 지정할 것.
    --frames a,b,c  프레임 번호 직접 (기존 방식)
    --list          스텝/프레임/온도 대응표만 출력하고 종료 (odb 확인용)
    --out DIR       기본: odb 폴더
    --auto          범례 자동 스케일 (고정 해제)

산출 (temps 모드):
    <out>/img_<변수>_<그룹>_T####C.png    예: img_S11_matrix_T0750C.png
(frames 모드는 기존처럼 _f## 이름)

논문 범례 고정값: 기지 S11 -160~+310 / 얀 S11 -600~+270 / 손상 0~1.
범례를 고정해야 온도끼리 색이 비교된다.

주의: 렌더링은 Abaqus CAE 커널에서만 돈다. 여기서는 프레임 선택
로직만 검증했고 실제 그림은 워크스테이션에서 확인해야 한다.
"""
from __future__ import print_function

import sys
import os
import glob
import re

MATRIX_SETS = ('MATRIX',)
YARN_SETS = ('YARN0', 'YARN1', 'YARN2', 'YARN3')

# 논문 범례 고정값 (Fig.3/7/9 판독; 손상은 전 그림 0~1)
LIMITS = {'S11': {'matrix': (-160.0, 310.0), 'yarn': (-600.0, 270.0)}}
DMG_LIM = (0.0, 1.0)

# 프리셋: (그룹이름, set 종류 M/Y, 변수 별칭 후보[우선순위], 파일태그)
#   덱이 *Depvar 이름을 정의했으면 SDV_DMT 형태, 아니면 SDVn 만 있다.
#   우리 UMAT 번호: 기지 SV1=DMT / 얀 SV1=DY1T, SV3=DYTT. 같은 SDV1 이라도
#   기지 요소 위에서는 DMT, 얀 요소 위에서는 DY1T 이므로 그룹만 갈라
#   그리면 안전하다.
FIG_STRESS = [('matrix', 'M', ['S11'], 'S11'),
              ('yarn', 'Y', ['S11'], 'S11')]
# 이름 있는 덱(기존, SDV_DMT 식) 을 먼저 찾고, 없으면 번호로 떨어진다.
# 번호는 V2_7P 배치 기준: 논문과 같은 SDV14(기지)/SDV1(얀 종)/SDV2(얀 횡).
# 이름 없는 덱은 반드시 V2_7P 와 짝지어 돌린다는 전제다.
FIG_DAMAGE = [('matrix', 'M', ['SDV_DMT', 'SDV14'], 'DMT'),
              ('yarnL', 'Y', ['SDV_DY1T', 'SDV1'], 'DY1T'),
              ('yarnT', 'Y', ['SDV_DYTT', 'SDV2'], 'DYTT')]


def argval(args, key, default=None):
    if key in args:
        i = args.index(key)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def step_trange(name):
    """Step 이름에서 (시작온도, 끝온도) 를 추정한다. 모르면 None."""
    u = name.upper()
    if 'COOL' in u:
        return (1050.0, 23.0)
    if 'HEAT' in u:
        m = re.search(r'(\d{3,4})', u)
        if m:
            return (23.0, float(m.group(1)))
        return None
    if 'TENSION' in u:
        m = re.search(r'(\d{1,4})\s*C', u)
        if m:
            t = float(m.group(1))
            return (t, t)
        return None
    return None


def frames_from_temps(temps, trange, fvals):
    """온도 목록 -> [(프레임번호, 실제온도)]. fvals = frameValue 목록."""
    A, B = trange
    if A == B:
        return None
    out = []
    for T in temps:
        ft = (T - A) / (B - A)
        best, bd = 0, 1.0e30
        for i in range(len(fvals)):
            d = abs(fvals[i] - ft)
            if d < bd:
                best, bd = i, d
        out.append((best, A + (B - A) * fvals[best]))
    return out


def build_renders(fig, var):
    if fig == 'stress':
        return FIG_STRESS
    if fig == 'damage':
        return FIG_DAMAGE
    v = (var or 'S11')
    return [('matrix', 'M', [v], v.upper()),
            ('yarn', 'Y', [v], v.upper())]


def limits_for(tagvar, gname, fig, auto):
    if auto:
        return None
    u = tagvar.upper()
    if fig == 'damage' or u.startswith(('DMT', 'DMC', 'DY', 'SDV')):
        return DMG_LIM
    base = 'matrix' if gname == 'matrix' else 'yarn'
    return LIMITS.get(u, {}).get(base)


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
    if '--' in args:
        args = args[args.index('--') + 1:]
    paths = [a for a in args if a.lower().endswith('.odb')]
    if not paths:
        print('usage: abaqus cae noGUI=make_odb_images.py -- <job>.odb '
              '[--fig stress|damage] [--step NAME] '
              '[--temps 1050,750,500,250,23] [--trange A,B] '
              '[--frames 0,25] [--var S11] [--out DIR] [--list] [--auto]')
        return 1
    path = paths[0]
    fig = argval(args, '--fig')
    if fig and fig not in ('stress', 'damage'):
        print('[error] --fig must be stress or damage')
        return 1
    var = argval(args, '--var')
    outdir = argval(args, '--out') or (os.path.dirname(os.path.abspath(path))
                                       or '.')
    auto = '--auto' in args
    listonly = '--list' in args

    from abaqus import session
    from abaqusConstants import (CONTOURS_ON_DEF, INTEGRATION_POINT,
                                 COMPONENT, INVARIANT, OFF, ON, PNG)
    # displayGroupOdbToolset(dgo) 는 visualization 모듈이 등록해 줘야
    # 보인다. noGUI 커널은 아무 모듈도 자동 import 하지 않으므로
    # visualization 을 먼저 불러야 한다 (cae/viewer 공통 -- 이전의
    # "viewer 커널에는 dgo 가 없다" 진단은 틀렸다. cae 에서도 같은
    # ImportError 가 났고, 원인은 이 선행 import 누락이었다).
    try:
        import visualization  # noqa: F401 -- dgo 등록 부수효과가 목적
        import displayGroupOdbToolset as dgo
    except ImportError:
        print('')
        print('[error] visualization/displayGroupOdbToolset 를 불러올 수'
              ' 없다.')
        print('        abaqus cae noGUI= 로 실행 중인지 확인할 것.')
        print('        (abaqus python 으로는 이 스크립트를 돌릴 수 없다.)')
        return 3

    if not check_odb_path(path):
        return 2
    # CAE 의 session.openOdb 는 odbAccess.openOdb 와 시그니처가 다르다.
    # 첫 인자가 위치인자(name)이라 path= 키워드만 주면
    # "expected 1, got 0" TypeError 가 난다. 위치인자로 넘긴다.
    try:
        odb = session.openOdb(path, readOnly=True)
    except (TypeError, ValueError):
        odb = session.openOdb(path)
    print('odb   : %s' % os.path.basename(path))

    # ---- Step 선택 -------------------------------------------------------
    want = argval(args, '--step')
    sname = None
    if want:
        for k in odb.steps.keys():
            if k.upper() == want.upper():
                sname = k
                break
        if sname is None:
            print('[error] step %s not in odb. steps: %s'
                  % (want, ', '.join(odb.steps.keys())))
            return 2
    else:
        for k in odb.steps.keys():
            if 'COOL' in k.upper():
                sname = k
                break
        if sname is None:
            sname = list(odb.steps.keys())[0]
    st = odb.steps[sname]
    nfr = len(st.frames)
    fvals = [st.frames[i].frameValue for i in range(nfr)]
    print('step  : %s  (%d frames)' % (sname, nfr))
    if nfr == 0:
        print('[error] step has no frames (never ran?)')
        return 2

    # ---- 온도 구간 -------------------------------------------------------
    tr_arg = argval(args, '--trange')
    if tr_arg:
        p = tr_arg.split(',')
        trange = (float(p[0]), float(p[1]))
    else:
        trange = step_trange(sname)
    if trange:
        print('trange: %.0f -> %.0f C  %s'
              % (trange[0], trange[1],
                 '(--trange)' if tr_arg else '(step name auto)'))
    else:
        print('trange: unknown (give --trange A,B for temperature mode)')

    # ---- --list: 대응표만 찍고 끝 ---------------------------------------
    if listonly:
        print('')
        print('  %-6s %-10s %-10s' % ('frame', 'stepTime', 'T [C]'))
        stride = max(1, nfr // 25)
        idx = list(range(0, nfr, stride))
        if idx[-1] != nfr - 1:
            idx.append(nfr - 1)
        for i in idx:
            if trange and trange[0] != trange[1]:
                t = '%8.1f' % (trange[0]
                               + (trange[1] - trange[0]) * fvals[i])
            else:
                t = '     - '
            print('  %-6d %-10.4f %s' % (i, fvals[i], t))
        print('')
        print('all steps: %s' % ', '.join(odb.steps.keys()))
        odb.close()
        return 0

    # ---- 프레임 선택: temps > frames > 기본 5장 --------------------------
    temps_arg = argval(args, '--temps')
    fr_arg = argval(args, '--frames')
    sel = []                          # (frame, 실제온도 or None, 파일라벨)
    if temps_arg:
        if not trange or trange[0] == trange[1]:
            print('[error] this step has no temperature ramp (or unknown).'
                  ' Give --trange A,B, or use --frames.')
            return 2
        temps = [float(x) for x in temps_arg.split(',') if x.strip() != '']
        got = frames_from_temps(temps, trange, fvals)
        for (fi, Tact), Twant in zip(got, temps):
            if abs(Tact - Twant) > 25.0:
                print('  [warn] requested %.0fC -> nearest frame %d is '
                      'only %.1fC (off %.0fK)'
                      % (Twant, fi, Tact, abs(Tact - Twant)))
            sel.append((fi, Tact, 'T%04dC' % int(round(Twant))))
    elif fr_arg:
        for x in fr_arg.split(','):
            fi = int(x)
            if 0 <= fi < nfr:
                T = None
                if trange:
                    T = trange[0] + (trange[1] - trange[0]) * fvals[fi]
                sel.append((fi, T, 'f%02d' % fi))
    else:
        for fi in sorted(set(int(round(f * (nfr - 1)))
                             for f in (0.0, 0.25, 0.5, 0.75, 1.0))):
            T = None
            if trange:
                T = trange[0] + (trange[1] - trange[0]) * fvals[fi]
            sel.append((fi, T, 'f%02d' % fi))
    if not sel:
        print('[error] no valid frames selected')
        return 2
    print('frames: %s' % [s[0] for s in sel])

    # ---- set 이름 해석 (어셈블리 -> 인스턴스 순) -------------------------
    def full_setnames(wanted):
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
                have = dict((k.upper(), k)
                            for k in inst.elementSets.keys())
                if u in have:
                    found = '%s.%s' % (iname, have[u])
                    break
            if found:
                out.append(found)
            else:
                print('  [warn] elementSet %s not found' % w)
        return tuple(out)

    msets = full_setnames(MATRIX_SETS)
    ysets = full_setnames(YARN_SETS)

    # ---- 변수 이름 해석 (SDV_DMT 가 없으면 SDV1 로) ----------------------
    fo_names = list(st.frames[sel[0][0]].fieldOutputs.keys())

    def resolve_var(cands):
        for c in cands:
            cu = c.upper()
            if cu in ('S11', 'S22', 'S33', 'MISES'):
                return cu
            for n in fo_names:
                if n.upper() == cu:
                    return n
        return None

    renders = build_renders(fig, var)

    # noGUI 커널은 기본 뷰포트를 안 만드는 설치본이 있다. 없으면 만든다.
    vkeys = list(session.viewports.keys())
    if vkeys:
        vp = session.viewports[vkeys[0]]
    else:
        vp = session.Viewport(name='render', width=200, height=150)
    vp.setValues(displayedObject=odb)
    vp.makeCurrent()
    vp.maximize()
    vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
    # 논문 그림과 같은 등각 시점. 마음에 안 들면 GUI 에서 맞춘 뒤
    # View > Save 로 저장한 이름을 여기 넣으면 된다.
    try:
        vp.view.setValues(session.views['Iso'])
        vp.view.fitView()
    except Exception:
        pass
    session.printOptions.setValues(vpDecorations=OFF, reduceColors=False)
    session.pngOptions.setValues(imageSize=(1600, 1200))
    # 논문 범례와 같은 12구간
    vp.odbDisplay.contourOptions.setValues(numIntervals=12)

    made = 0
    for gname, kind, cands, tagvar in renders:
        sets = msets if kind == 'M' else ysets
        if not sets:
            continue
        vname = resolve_var(cands)
        if vname is None:
            print('  [error] none of %s in odb fields. have: %s ...'
                  % (cands, ', '.join(fo_names[:10])))
            continue
        if vname == 'MISES':
            vp.odbDisplay.setPrimaryVariable(
                variableLabel='S', outputPosition=INTEGRATION_POINT,
                refinement=(INVARIANT, 'Mises'))
        elif vname in ('S11', 'S22', 'S33'):
            vp.odbDisplay.setPrimaryVariable(
                variableLabel='S', outputPosition=INTEGRATION_POINT,
                refinement=(COMPONENT, vname))
        else:
            try:
                vp.odbDisplay.setPrimaryVariable(
                    variableLabel=vname,
                    outputPosition=INTEGRATION_POINT)
            except Exception as e:
                print('  [error] variable %s: %s' % (vname, e))
                continue
        vp.odbDisplay.displayGroup.replace(
            leaf=dgo.LeafFromElementSets(elementSets=sets))
        lim = limits_for(tagvar, gname, fig, auto)
        if lim:
            vp.odbDisplay.contourOptions.setValues(
                minAutoCompute=OFF, minValue=lim[0],
                maxAutoCompute=OFF, maxValue=lim[1])
        else:
            vp.odbDisplay.contourOptions.setValues(
                minAutoCompute=ON, maxAutoCompute=ON)
        for fi, Tact, lab in sel:
            vp.odbDisplay.setFrame(step=sname, frame=fi)
            fn = os.path.join(outdir,
                              'img_%s_%s_%s' % (tagvar, gname, lab))
            session.printToFile(fileName=fn, format=PNG,
                                canvasObjects=(vp,))
            made += 1
            print('  %-7s %-5s frame %3d  %s -> %s.png'
                  % (gname, tagvar, fi,
                     ('T=%7.1fC' % Tact) if Tact is not None else '',
                     os.path.basename(fn)))

    odb.close()
    print('')
    print('wrote %d images in %s' % (made, outdir))
    if fig == 'damage':
        print('paper Fig.5/8/10 rows: matrix / longitudinal / transverse')
    else:
        print('paper Fig.3/7/9 style: top row = matrix, bottom = yarns')
    return 0


class _Tee(object):
    """화면과 파일에 동시에 쓴다.

    `abaqus cae noGUI=` 커널은 스크립트의 stdout 을 콘솔에 안 남기고
    끝나는 경우가 있다(6.18 확인). 그러면 실패해도 화면에 아무것도
    안 뜨므로 원인을 알 수 없다. 무조건 로그 파일을 남긴다.
    """

    def __init__(self, stream, fh):
        self.stream = stream
        self.fh = fh

    def write(self, s):
        for t in (self.stream, self.fh):
            try:
                t.write(s)
                t.flush()
            except Exception:
                pass

    def flush(self):
        for t in (self.stream, self.fh):
            try:
                t.flush()
            except Exception:
                pass


if __name__ == '__main__':
    _log = os.path.join(os.getcwd(), 'make_odb_images_log.txt')
    _fh = None
    try:
        # 이어쓰기다. Fig.3 과 Fig.5 처럼 연속으로 두 번 돌리면 예전엔
        # 앞 실행 로그가 지워져서 성공 여부를 확인할 수 없었다.
        _fh = open(_log, 'a')
        sys.stdout = _Tee(sys.stdout, _fh)
        sys.stderr = _Tee(sys.stderr, _fh)
        print('')
        print('=' * 62)
        print('log   : %s' % _log)
        print('argv  : %s' % ' '.join(sys.argv[1:]))
    except IOError:
        pass
    try:
        import traceback
        _rc = 0
        try:
            _rc = main()
        except Exception:
            traceback.print_exc()
            _rc = 9
        print('exit  : %s' % _rc)
    finally:
        if _fh is not None:
            try:
                _fh.close()
            except Exception:
                pass
