#!/usr/bin/env bash
# verify_diagnostic_inert.sh — prove that the V2_7D yarn diagnostic SDV17
# changes nothing, and that it is not vacuous.
#
# V2_7D adds one state variable to KYARN_UPDATE: the shear share of the
# Eq.11 longitudinal tensile criterion, latched at onset. The claim is
# that it is PHYSICALLY INERT — no equation reads SV(17) back, so every
# quantity Abaqus consumes is unchanged. A claim like that is worth
# nothing unless it is tested, so this drives V2_7P and V2_7D through the
# same strain histories with the same yarn card and compares:
#
#   state.txt  STRESS(6), CTAN(6,6), SV(1..16), PNEWDT
#              MUST BE IDENTICAL  -> the change is inert
#   shr.txt    SV(17)
#              MUST DIFFER        -> the diagnostic is not vacuous
#
# The second half matters as much as the first: an inert change that also
# does nothing would pass the first test trivially. Same discipline as
# the --selftest negative control in audit_temperature_props.py.
#
# usage: verify_diagnostic_inert.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRCP="$HERE/../src/UMAT_CSIC_RVE_DAMAGE_V2_7P.for"
SRCD="$HERE/../src/UMAT_CSIC_RVE_DAMAGE_V2_7D.for"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

printf '      IMPLICIT REAL*8(A-H,O-Z)\n' > "$TMP/ABA_PARAM.INC"
cp "$SRCP" "$TMP/p.f"
cp "$SRCD" "$TMP/d.f"

# ---- shims: one call signature for the driver, two for the UMATs -----
cat > "$TMP/shim_p.f" <<'EOF'
      SUBROUTINE KYCALL(EPS,STRESS,CTAN,SV,P,NP,NSV,DTIME,TEMP,
     1 DTEMP,PNEWDT,KSTEP,CELENT)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      INTEGER NP,NSV,KSTEP
      CALL KYARN_UPDATE(EPS,STRESS,CTAN,SV,P,NP,DTIME,TEMP,
     1 DTEMP,PNEWDT,KSTEP,CELENT)
      RETURN
      END
EOF
cat > "$TMP/shim_d.f" <<'EOF'
      SUBROUTINE KYCALL(EPS,STRESS,CTAN,SV,P,NP,NSV,DTIME,TEMP,
     1 DTEMP,PNEWDT,KSTEP,CELENT)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      INTEGER NP,NSV,KSTEP
      CALL KYARN_UPDATE(EPS,STRESS,CTAN,SV,P,NP,NSV,DTIME,TEMP,
     1 DTEMP,PNEWDT,KSTEP,CELENT)
      RETURN
      END
EOF
cat > "$TMP/xit.f" <<'EOF'
      SUBROUTINE XIT
      WRITE(*,*) 'UMAT called XIT -- material card rejected.'
      STOP 1
      END
EOF

# ---- driver: real P2/P3 yarn card, four strain paths ----------------
cat > "$TMP/drv.f" <<'EOF'
      PROGRAM DRV
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(17),P(38)
      DOUBLE PRECISION DE(6,4),XTV(2),GFV(2)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      INTEGER I,J,IC,IX,IG,INC,NP,NSV,KSTEP
C
      NP=38
      NSV=17
      KSTEP=1
      DTIME=1.0D-2
      TEMP=23.0D0
      DTEMP=0.0D0
      CELENT=0.1D0
C     Yarn card as shipped in ZHANG2022_*_V2_0.inp.
      P(1)=1.0D0
      P(2)=254967.228042D0
      P(3)=44321.737572D0
      P(4)=44321.737572D0
      P(5)=0.247516386D0
      P(6)=0.247516386D0
      P(7)=0.395813581D0
      P(8)=26431.515264D0
      P(9)=26431.515264D0
      P(10)=15876.667974D0
      P(11)=2835.0D0
      P(12)=1956.0D0
      P(13)=80.0D0
      P(14)=350.0D0
      P(15)=120.0D0
      P(16)=120.0D0
      P(17)=100.0D0
      P(18)=2.0D0
      P(19)=2.0D0
      P(20)=2.0D0
      P(21)=2.0D0
      P(22)=0.99D0
      P(23)=0.99D0
      P(24)=0.02D0
      P(25)=0.10D0
      P(26)=3.0D0
      P(27)=0.25D0
      P(28)=1.0D0
      P(29)=1.15D0
      P(30)=0.75D0
      P(31)=0.50D0
      P(32)=0.0D0
      P(33)=12.5D0
      P(34)=0.0D0
      P(35)=0.0D0
      P(36)=700.0D0
      P(37)=3.0D0
      P(38)=8000.0D0
C     XT: 421 is the P2 back-calibration, 2835 the paper's own value.
      XTV(1)=421.0D0
      XTV(2)=2835.0D0
C     GF1T: 0 disables the crack band, 0.03962 is the P2 value.
      GFV(1)=0.0D0
      GFV(2)=0.03962D0
C     Strain paths, chosen so the 1T mode initiates under four
C     different mixes of axial and shear.
      DO I=1,6
         DO J=1,4
            DE(I,J)=0.0D0
         END DO
      END DO
      DE(1,1)=1.0D-4
      DE(1,2)=1.0D-4
      DE(4,2)=1.0D-4
      DE(1,3)=1.0D-5
      DE(4,3)=2.0D-4
      DE(1,4)=-1.0D-4
C
      OPEN(8,FILE='state.txt',STATUS='REPLACE')
      OPEN(9,FILE='shr.txt',STATUS='REPLACE')
      DO IX=1,2
      DO IG=1,2
      DO IC=1,4
         P(11)=XTV(IX)
         P(32)=GFV(IG)
         DO I=1,17
            SV(I)=0.0D0
         END DO
         DO I=1,6
            EPS(I)=0.0D0
            STRESS(I)=0.0D0
         END DO
         DO INC=1,200
            DO I=1,6
               EPS(I)=EPS(I)+DE(I,IC)
            END DO
            PNEWDT=1.0D0
            CALL KYCALL(EPS,STRESS,CTAN,SV,P,NP,NSV,DTIME,TEMP,
     1           DTEMP,PNEWDT,KSTEP,CELENT)
            IF (MOD(INC,10).EQ.0) THEN
               WRITE(8,900) IX,IG,IC,INC,'PNEWDT',0,PNEWDT
               DO I=1,6
                  WRITE(8,900) IX,IG,IC,INC,'STRESS',I,STRESS(I)
               END DO
               DO I=1,6
                  DO J=1,6
                     WRITE(8,901) IX,IG,IC,INC,'CTAN',I,J,CTAN(I,J)
                  END DO
               END DO
               DO I=1,16
                  WRITE(8,900) IX,IG,IC,INC,'SV',I,SV(I)
               END DO
C              SV(5)=R1T rides along because SDV17=0 is ambiguous on
C              its own: it means both "killed by s11 alone" and "never
C              initiated". R1T>=1 is what separates them.
               WRITE(9,902) IX,IG,IC,INC,SV(5),SV(17)
            END IF
         END DO
      END DO
      END DO
      END DO
      CLOSE(8)
      CLOSE(9)
  900 FORMAT(4I5,1X,A8,1X,I3,4X,ES25.17)
  901 FORMAT(4I5,1X,A8,1X,I3,I4,ES25.17)
  902 FORMAT(4I5,1X,ES25.17,1X,ES25.17)
      END
EOF

FC="gfortran -ffixed-form -ffixed-line-length-72 -std=legacy -w"
cd "$TMP"
$FC -c p.f -o p.o
$FC -c d.f -o d.o
$FC -c xit.f -o xit.o
$FC -c drv.f -o drv.o
$FC -c shim_p.f -o shim_p.o
$FC -c shim_d.f -o shim_d.o
mkdir -p runP runD
$FC drv.o shim_p.o p.o xit.o -o runP/a.out
$FC drv.o shim_d.o d.o xit.o -o runD/a.out
(cd runP && ./a.out)
(cd runD && ./a.out)

FAIL=0
echo "== 1) inertness: STRESS / CTAN / SV(1..16) / PNEWDT =="
N=$(wc -l < runP/state.txt)
if diff -q runP/state.txt runD/state.txt > /dev/null; then
  echo "   PASS  $N values identical to 17 significant digits"
  echo "         (V2_7D is bit-exact with V2_7P for everything Abaqus reads)"
else
  echo "   FAIL  V2_7D changed the response:"
  diff runP/state.txt runD/state.txt | head -20
  FAIL=1
fi

echo "== 2) not vacuous: SDV17 must be populated in V2_7D and 0 in V2_7P =="
if diff -q runP/shr.txt runD/shr.txt > /dev/null; then
  echo "   FAIL  SDV17 is identical in both -- the diagnostic never fires."
  FAIL=1
else
  ZP=$(awk '$6+0!=0' runP/shr.txt | wc -l)
  NZ=$(awk '$6+0!=0' runD/shr.txt | wc -l)
  echo "   PASS  V2_7P nonzero SDV17: $ZP (expected 0)"
  echo "         V2_7D nonzero SDV17: $NZ"
  [ "$ZP" -eq 0 ] || { echo "   FAIL  V2_7P wrote SDV17."; FAIL=1; }
  [ "$NZ" -gt 0 ] || { echo "   FAIL  V2_7D never latched."; FAIL=1; }
fi

echo "== 3) the number itself: shear share at 1T onset =="
echo "   Prescribed single-point strain paths, NOT the RVE. The absolute"
echo "   value depends on the axial:shear ratio imposed here, so read the"
echo "   421 -> 2835 SHIFT, not the numbers. The RVE value is what the"
echo "   P3 batch will report."
echo
echo "   XT     path                     onset   SDV17"
awk '$5+0>=1 {k=$1" "$3; if(!(k in seen)){seen[k]=$6}}
     END{
       split("421 2835",xt," ");
       split("axial|axial+shear|shear-dominant|compression",pn,"|");
       for(i=1;i<=2;i++)for(c=1;c<=4;c++){
         k=i" "c;
         if(k in seen){o="yes"; v=sprintf("%.4f",seen[k])}
         else         {o="no ";  v="(1T never initiated)"}
         printf "   %-6s %-24s %-7s %s\n", xt[i], pn[c], o, v
       }
     }' runD/shr.txt

if [ "$FAIL" -eq 0 ]; then
  echo
  echo "ALL PASS — SDV17 is inert and non-vacuous."
else
  echo
  echo "FAILED"
fi
exit "$FAIL"
