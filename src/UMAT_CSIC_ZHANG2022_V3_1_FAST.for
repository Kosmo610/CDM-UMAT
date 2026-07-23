C=======================================================================
C  UMAT_CSIC_ZHANG2022_V3_1_FAST.for
C
C  Paper-faithful baseline for:
C  Q. Zhang et al., Ceramics International 48 (2022) 3109-3124.
C
C  Main corrections from the user's V2_2 code:
C   1) Yarn: 3-D Hashin initiation in effective-stress space.
C   2) Yarn: exponential evolution, with mixed linear-exponential
C      law for longitudinal tensile damage.
C   3) Yarn/matrix stiffness: damaged COMPLIANCE formulation.
C   4) Matrix: J2 elastoplasticity with associated flow and isotropic
C      linear hardening in effective-stress space.
C   5) Matrix damage initiation: von Mises / Xt or Xc, selected by
C      the sign of the first stress invariant.
C   6) Matrix DDSDDE: radial-return algorithmic elastoplastic tangent
C      mapped to the damaged nominal-stress space.
C   7) Damage: viscous regularization, bounded jump control, and a
C      residual-stiffness cap are retained as numerical controls.
C   8) Removed Weibull strength, Rankine initiation, crack closure,
C      and temperature-dependent material parameters that are not in
C      the target paper.
C
C  RECOMMENDED FAST-VERIFICATION INPUT CONTROLS:
C    ETA = 1.0E-4, DJMAX = 0.05, PMIN = 0.20, DMAX = 0.99.
C    These remain PROPS inputs; the UMAT does not silently overwrite
C    positive user values. Use the companion INP patch script.
C
C  IMPORTANT LIMITATION:
C  The target paper does not publish the matrix hardening curve,
C  fracture energies/softening factors, or longitudinal mixed-law
C  calibration parameters. These remain calibration inputs. Therefore
C  this file reproduces the published MODEL FORM, but cannot guarantee
C  identical numerical curves without inverse calibration.
C
C  Abaqus Voigt order: 11,22,33,12,13,23; engineering shear strain.
C=======================================================================
      SUBROUTINE UMAT(STRESS,STATEV,DDSDDE,SSE,SPD,SCD,
     1 RPL,DDSDDT,DRPLDE,DRPLDT,STRAN,DSTRAN,TIME,DTIME,TEMP,
     2 DTEMP,PREDEF,DPRED,CMNAME,NDI,NSHR,NTENS,NSTATV,PROPS,
     3 NPROPS,COORDS,DROT,PNEWDT,CELENT,DFGRD0,DFGRD1,
     4 NOEL,NPT,LAYER,KSPT,KSTEP,KINC)
      INCLUDE 'ABA_PARAM.INC'
      CHARACTER*80 CMNAME
      DIMENSION STRESS(NTENS),STATEV(NSTATV),
     1 DDSDDE(NTENS,NTENS),DDSDDT(NTENS),DRPLDE(NTENS),
     2 STRAN(NTENS),DSTRAN(NTENS),TIME(2),PREDEF(1),DPRED(1),
     3 PROPS(NPROPS),COORDS(3),DROT(3,3),DFGRD0(3,3),
     4 DFGRD1(3,3)
      DOUBLE PRECISION EPS(6),SOLD(6),SSE0,WORK,DW
      INTEGER I,J
C
      IF (NTENS.NE.6 .OR. NDI.NE.3 .OR. NSHR.NE.3) THEN
         WRITE(7,*) 'ZHANG2022 UMAT requires 3-D solid elements.'
         CALL XIT
      END IF
      DO I=1,6
         EPS(I)=STRAN(I)+DSTRAN(I)
         SOLD(I)=STRESS(I)
         DDSDDT(I)=0.0D0
         DRPLDE(I)=0.0D0
         DO J=1,6
            DDSDDE(I,J)=0.0D0
         END DO
      END DO
      SSE0=SSE
      SCD=0.0D0
      RPL=0.0D0
      DRPLDT=0.0D0
      IF (PNEWDT.LE.0.0D0) PNEWDT=1.0D0
C
      IF (INDEX(CMNAME,'YARN').GT.0) THEN
         IF (NPROPS.LT.31 .OR. NSTATV.LT.12) THEN
            WRITE(7,*) 'YARN: NPROPS>=31 and NSTATV>=12 required.'
            CALL XIT
         END IF
         CALL KYARN_Z22(EPS,STRESS,DDSDDE,STATEV,PROPS,
     1        DTIME,TEMP,DTEMP,PNEWDT)
      ELSE IF (INDEX(CMNAME,'MATRIX').GT.0) THEN
         IF (NPROPS.LT.15 .OR. NSTATV.LT.14) THEN
            WRITE(7,*) 'MATRIX: NPROPS>=15 and NSTATV>=14 required.'
            CALL XIT
         END IF
         CALL KMATRIX_Z22(EPS,STRESS,DDSDDE,STATEV,PROPS,
     1        DTIME,TEMP,DTEMP,PNEWDT)
      ELSE
         WRITE(7,*) 'Unknown CMNAME: ',CMNAME
         CALL XIT
      END IF
C
C     Diagnostic energy bookkeeping only.
      WORK=0.0D0
      SSE=0.0D0
      DO I=1,6
         WORK=WORK+0.5D0*(SOLD(I)+STRESS(I))*DSTRAN(I)
         SSE=SSE+0.5D0*STRESS(I)*EPS(I)
      END DO
      DW=WORK-(SSE-SSE0)
      SPD=MAX(SPD,SPD+MAX(0.0D0,DW))
      RETURN
      END
C=======================================================================
      SUBROUTINE KYARN_Z22(EPS,SIG,CTAN,SV,P,DTIME,TEMP,
     1 DTEMP,PNEWDT)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),SIG(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT
      DOUBLE PRECISION C0(6,6),CD(6,6),SE(6),SD(6,6)
      DOUBLE PRECISION E1,E2,E3,N12,N13,N23,G12,G13,G23
      DOUBLE PRECISION XT,XC,YT,YC,S12,S13,S23
      DOUBLE PRECISION A1T,A1C,A2T,A2C,K1,RFTR,DFTR,XPO
      DOUBLE PRECISION ETA,DJMAX,PMIN,ENABLE,DMAX
      DOUBLE PRECISION F1T,F1C,F2T,F2C,SUMT,TERM
      DOUBLE PRECISION R1T,R1C,R2T,R2C
      DOUBLE PRECISION D1T0,D1C0,D2T0,D2C0
      DOUBLE PRECISION D1T,D1C,D2T,D2C,D1,D2,D12,D13,D23
      DOUBLE PRECISION TAR,GAM,DJ,TEND,RFAC,REQ
      INTEGER I,J,MODE
C
      E1=P(2)
      E2=P(3)
      E3=P(4)
      N12=P(5)
      N13=P(6)
      N23=P(7)
      G12=P(8)
      G13=P(9)
      G23=P(10)
      XT=P(11)
      XC=P(12)
      YT=P(13)
      YC=P(14)
      S12=P(15)
      S13=P(16)
      S23=P(17)
      A1T=P(18)
      A1C=P(19)
      A2T=P(20)
      A2C=P(21)
      K1=P(22)
      RFTR=P(23)
      DFTR=P(24)
      XPO=P(25)
      ETA=P(26)
      DJMAX=P(27)
      PMIN=P(28)
      ENABLE=P(29)
      DMAX=P(30)
      IF (ETA.LE.0.0D0) ETA=1.0D-4
      IF (DJMAX.LE.0.0D0) DJMAX=5.0D-2
      IF (PMIN.LE.0.0D0) PMIN=2.0D-1
      IF (DMAX.LE.0.0D0) DMAX=9.9D-1
      DMAX=MIN(9.999D-1,MAX(0.0D0,DMAX))
C
      CALL KORTHO_Z22(E1,E2,E3,N12,N13,N23,
     1 G12,G13,G23,C0)
      CALL KMATVEC6_Z22(C0,EPS,SE)
C
C     3-D Hashin criteria, effective stress, alpha=beta=1.
      F1T=0.0D0
      F1C=0.0D0
      F2T=0.0D0
      F2C=0.0D0
      IF (SE(1).GE.0.0D0) THEN
         F1T=SQRT((SE(1)/XT)**2+(SE(4)/S12)**2+
     1        (SE(5)/S13)**2)
      ELSE
         F1C=ABS(SE(1))/XC
      END IF
      SUMT=SE(2)+SE(3)
      IF (SUMT.GE.0.0D0) THEN
         TERM=(SUMT/YT)**2+(SE(6)*SE(6)-SE(2)*SE(3))/
     1        (S23*S23)+(SE(4)/S12)**2+(SE(5)/S13)**2
         F2T=SQRT(MAX(0.0D0,TERM))
      ELSE
         TERM=((YC/(2.0D0*S23))**2-1.0D0)*SUMT/YC+
     1        (SUMT/(2.0D0*S23))**2+
     2        (SE(6)*SE(6)-SE(2)*SE(3))/(S23*S23)+
     3        (SE(4)/S12)**2+(SE(5)/S13)**2
         F2C=SQRT(MAX(0.0D0,TERM))
      END IF
C
      D1T0=MAX(0.0D0,MIN(DMAX,SV(3)))
      D1C0=MAX(0.0D0,MIN(DMAX,SV(4)))
      D2T0=MAX(0.0D0,MIN(DMAX,SV(5)))
      D2C0=MAX(0.0D0,MIN(DMAX,SV(6)))
      R1T=MAX(MAX(1.0D0,SV(7)),F1T)
      R1C=MAX(MAX(1.0D0,SV(8)),F1C)
      R2T=MAX(MAX(1.0D0,SV(9)),F2T)
      R2C=MAX(MAX(1.0D0,SV(10)),F2C)
      D1T=D1T0
      D1C=D1C0
      D2T=D2T0
      D2C=D2C0
      IF (ENABLE.GT.0.5D0) THEN
         IF (ETA.GT.0.0D0) THEN
            GAM=DTIME/(ETA+DTIME)
         ELSE
            GAM=1.0D0
         END IF
         GAM=MIN(1.0D0,MAX(0.0D0,GAM))
         CALL KMIXED_Z22(R1T,A1T,K1,E1,RFTR,DFTR,
     1        XT,XPO,DMAX,TAR)
         D1T=MAX(D1T0,D1T0+GAM*(TAR-D1T0))
         CALL KEXPDMG_Z22(R1C,A1C,DMAX,TAR)
         D1C=MAX(D1C0,D1C0+GAM*(TAR-D1C0))
         CALL KEXPDMG_Z22(R2T,A2T,DMAX,TAR)
         D2T=MAX(D2T0,D2T0+GAM*(TAR-D2T0))
         CALL KEXPDMG_Z22(R2C,A2C,DMAX,TAR)
         D2C=MAX(D2C0,D2C0+GAM*(TAR-D2C0))
      END IF
C
      D1=1.0D0-(1.0D0-D1T)*(1.0D0-D1C)
      D2=1.0D0-(1.0D0-D2T)*(1.0D0-D2C)
      D1=MIN(DMAX,MAX(0.0D0,D1))
      D2=MIN(DMAX,MAX(0.0D0,D2))
      D12=1.0D0-(1.0D0-D1)*(1.0D0-D2)
      D13=D12
      D23=1.0D0-(1.0D0-D2)*(1.0D0-D2)
C
C     Matzenmiller/Ge damaged compliance, then inversion.
      DO I=1,6
         DO J=1,6
            SD(I,J)=0.0D0
         END DO
      END DO
      SD(1,1)=1.0D0/((1.0D0-D1)*E1)
      SD(2,2)=1.0D0/((1.0D0-D2)*E2)
      SD(3,3)=1.0D0/((1.0D0-D2)*E3)
      SD(1,2)=-N12/E1
      SD(2,1)=SD(1,2)
      SD(1,3)=-N13/E1
      SD(3,1)=SD(1,3)
      SD(2,3)=-N23/E2
      SD(3,2)=SD(2,3)
      SD(4,4)=1.0D0/((1.0D0-D12)*G12)
      SD(5,5)=1.0D0/((1.0D0-D13)*G13)
      SD(6,6)=1.0D0/((1.0D0-D23)*G23)
      CALL KINV6_Z22(SD,CD)
      DO I=1,6
         DO J=1,6
            CTAN(I,J)=CD(I,J)
         END DO
      END DO
      CALL KMATVEC6_Z22(CD,EPS,SIG)
C
      MODE=1
      RFAC=R1T
      IF (R1C.GT.RFAC) THEN
         MODE=2
         RFAC=R1C
      END IF
      IF (R2T.GT.RFAC) THEN
         MODE=3
         RFAC=R2T
      END IF
      IF (R2C.GT.RFAC) THEN
         MODE=4
         RFAC=R2C
      END IF
      TEND=TEMP+DTEMP
      IF (SV(12).EQ.0.0D0 .AND. RFAC.GE.1.0D0) SV(12)=TEND
C     SDV1/2 match the paper's plotted yarn variables.
      SV(1)=D1
      SV(2)=D2
      SV(3)=D1T
      SV(4)=D1C
      SV(5)=D2T
      SV(6)=D2C
      SV(7)=R1T
      SV(8)=R1C
      SV(9)=R2T
      SV(10)=R2C
      SV(11)=DBLE(MODE)
C
      DJ=MAX(ABS(D1T-D1T0),ABS(D1C-D1C0),
     1       ABS(D2T-D2T0),ABS(D2C-D2C0))
      IF (DJMAX.GT.0.0D0 .AND. DJ.GT.DJMAX) THEN
         REQ=MAX(PMIN,0.8D0*DJMAX/DJ)
         PNEWDT=MIN(PNEWDT,REQ)
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KMATRIX_Z22(EPS,SIG,CTAN,SV,P,DTIME,TEMP,
     1 DTEMP,PNEWDT)
C     Isotropic J2 plasticity + scalar tensile/compressive damage.
C     Plastic return is performed in effective-stress space.
C     DDSDDE uses the exact radial-return algorithmic tangent for
C     linear isotropic hardening, then maps it into nominal-stress
C     space with the current frozen damage state.
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),SIG(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT
      DOUBLE PRECISION C0(6,6),S0(6,6),CD(6,6),SD(6,6)
      DOUBLE PRECISION CEP(6,6),MAPD(6,6)
      DOUBLE PRECISION EP0(6),EP(6),EELTR(6),SETR(6),SE(6)
      DOUBLE PRECISION E,NU,XT,XC,SY0,HISO,AT,AC,ETA
      DOUBLE PRECISION DJMAX,PMIN,ENABLE,DMAX,G,PEQ0,PEQ
      DOUBLE PRECISION PTRY,SDEV(6),QTR,SY,FY,DG,SCAL
      DOUBLE PRECISION RMT,RMC,DMT0,DMC0,DMT,DMC,DM
      DOUBLE PRECISION CRIT,TAR,GAM,DJ,REQ,I1,TEND,TOLY
      INTEGER I,J,MODE
C
      E=P(2)
      NU=P(3)
      XT=P(4)
      XC=P(5)
      SY0=P(6)
      HISO=P(7)
      AT=P(8)
      AC=P(9)
      ETA=P(10)
      DJMAX=P(11)
      PMIN=P(12)
      ENABLE=P(13)
      DMAX=P(14)
C     Defaults are used only if an input is absent/non-positive.
      IF (ETA.LE.0.0D0) ETA=1.0D-4
      IF (DJMAX.LE.0.0D0) DJMAX=5.0D-2
      IF (PMIN.LE.0.0D0) PMIN=2.0D-1
      IF (DMAX.LE.0.0D0) DMAX=9.9D-1
      DMAX=MIN(9.999D-1,MAX(0.0D0,DMAX))
      G=E/(2.0D0*(1.0D0+NU))
      CALL KISO_Z22(E,NU,C0)
      CALL KINV6_Z22(C0,S0)
C
      DO I=1,6
         EP0(I)=SV(I)
         EP(I)=EP0(I)
         EELTR(I)=EPS(I)-EP0(I)
      END DO
      PEQ0=MAX(0.0D0,SV(7))
      PEQ=PEQ0
      CALL KMATVEC6_Z22(C0,EELTR,SETR)
C
C     J2 radial return in undamaged/effective stress space.
      PTRY=(SETR(1)+SETR(2)+SETR(3))/3.0D0
      SDEV(1)=SETR(1)-PTRY
      SDEV(2)=SETR(2)-PTRY
      SDEV(3)=SETR(3)-PTRY
      SDEV(4)=SETR(4)
      SDEV(5)=SETR(5)
      SDEV(6)=SETR(6)
      CALL KMISES_Z22(SETR,QTR)
      SY=SY0+HISO*PEQ0
      FY=QTR-SY
      TOLY=1.0D-10*MAX(1.0D0,ABS(SY0),ABS(SY))
      DG=0.0D0
      IF (FY.GT.TOLY .AND. QTR.GT.1.0D-20) THEN
         DG=FY/(3.0D0*G+HISO)
         DG=MAX(0.0D0,DG)
         SCAL=MAX(0.0D0,1.0D0-3.0D0*G*DG/QTR)
         SE(1)=PTRY+SCAL*SDEV(1)
         SE(2)=PTRY+SCAL*SDEV(2)
         SE(3)=PTRY+SCAL*SDEV(3)
         SE(4)=SCAL*SDEV(4)
         SE(5)=SCAL*SDEV(5)
         SE(6)=SCAL*SDEV(6)
         EP(1)=EP0(1)+1.5D0*DG*SDEV(1)/QTR
         EP(2)=EP0(2)+1.5D0*DG*SDEV(2)/QTR
         EP(3)=EP0(3)+1.5D0*DG*SDEV(3)/QTR
         EP(4)=EP0(4)+3.0D0*DG*SDEV(4)/QTR
         EP(5)=EP0(5)+3.0D0*DG*SDEV(5)/QTR
         EP(6)=EP0(6)+3.0D0*DG*SDEV(6)/QTR
         PEQ=PEQ0+DG
         CALL KJ2ALG_Z31(E,NU,SDEV,QTR,DG,HISO,CEP)
      ELSE
         DO I=1,6
            SE(I)=SETR(I)
            DO J=1,6
               CEP(I,J)=C0(I,J)
            END DO
         END DO
      END IF
C
C     Paper Eq. (15)-(16): Mises criterion chosen by I1 sign.
      CALL KMISES_Z22(SE,CRIT)
      I1=SE(1)+SE(2)+SE(3)
      RMT=MAX(1.0D0,SV(10))
      RMC=MAX(1.0D0,SV(11))
      MODE=1
      IF (I1.GE.0.0D0) THEN
         RMT=MAX(RMT,CRIT/XT)
      ELSE
         RMC=MAX(RMC,CRIT/XC)
         MODE=2
      END IF
      DMT0=MAX(0.0D0,MIN(DMAX,SV(8)))
      DMC0=MAX(0.0D0,MIN(DMAX,SV(9)))
      DMT=DMT0
      DMC=DMC0
      IF (ENABLE.GT.0.5D0) THEN
         GAM=DTIME/(ETA+DTIME)
         GAM=MIN(1.0D0,MAX(0.0D0,GAM))
         CALL KEXPDMG_Z22(RMT,AT,DMAX,TAR)
         DMT=MAX(DMT0,DMT0+GAM*(TAR-DMT0))
         CALL KEXPDMG_Z22(RMC,AC,DMAX,TAR)
         DMC=MAX(DMC0,DMC0+GAM*(TAR-DMC0))
      END IF
      DM=1.0D0-(1.0D0-DMT)*(1.0D0-DMC)
      DM=MIN(DMAX,MAX(0.0D0,DM))
C
C     Ge-type damaged compliance for isotropic matrix.
      DO I=1,6
         DO J=1,6
            SD(I,J)=0.0D0
         END DO
      END DO
      SD(1,1)=1.0D0/((1.0D0-DM)*E)
      SD(2,2)=SD(1,1)
      SD(3,3)=SD(1,1)
      SD(1,2)=-NU/E
      SD(2,1)=SD(1,2)
      SD(1,3)=-NU/E
      SD(3,1)=SD(1,3)
      SD(2,3)=-NU/E
      SD(3,2)=SD(2,3)
      SD(4,4)=2.0D0*(1.0D0+NU)/((1.0D0-DM)*E)
      SD(5,5)=SD(4,4)
      SD(6,6)=SD(4,4)
      CALL KINV6_Z22(SD,CD)
C
C     Nominal stress: sigma = CD : (eps - epsp).
      DO I=1,6
         EELTR(I)=EPS(I)-EP(I)
      END DO
      CALL KMATVEC6_Z22(CD,EELTR,SIG)
C
C     Frozen-damage consistent tangent:
C       d sigma = CD*C0^{-1} : d effective_sigma
C       d effective_sigma = CEP : d epsilon.
      CALL KMATMUL6_Z31(CD,S0,MAPD)
      CALL KMATMUL6_Z31(MAPD,CEP,CTAN)
C     Remove round-off asymmetry for the symmetric Standard solver.
      DO I=1,6
         DO J=I+1,6
            CTAN(I,J)=0.5D0*(CTAN(I,J)+CTAN(J,I))
            CTAN(J,I)=CTAN(I,J)
         END DO
      END DO
C
      DO I=1,6
         SV(I)=EP(I)
      END DO
      SV(7)=PEQ
      SV(8)=DMT
      SV(9)=DMC
      SV(10)=RMT
      SV(11)=RMC
      SV(12)=DBLE(MODE)
      TEND=TEMP+DTEMP
      IF (SV(13).EQ.0.0D0 .AND.
     1   MAX(RMT,RMC).GT.1.0D0) SV(13)=TEND
      SV(14)=DM
C
C     Ask Abaqus to retry with a smaller increment only when the
C     regularized damage jump is still too large.
      DJ=MAX(ABS(DMT-DMT0),ABS(DMC-DMC0))
      IF (DJ.GT.DJMAX) THEN
         REQ=MAX(PMIN,0.8D0*DJMAX/DJ)
         PNEWDT=MIN(PNEWDT,REQ)
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KJ2ALG_Z31(E,NU,SDEV,QTR,DG,HISO,CALG)
C     Exact small-strain radial-return algorithmic tangent for J2
C     plasticity with linear isotropic hardening.
C
C     Engineering strain Voigt order: 11,22,33,12,13,23.
C     Stress Voigt shear components are tensor shears.
      IMPLICIT NONE
      DOUBLE PRECISION E,NU,SDEV(6),QTR,DG,HISO,CALG(6,6)
      DOUBLE PRECISION G,KMOD,AA,HR,RR,M(6),B(6),DEV(6)
      DOUBLE PRECISION TRB,MDOT,COEF,DS(6),DEN
      INTEGER I,J
      G=E/(2.0D0*(1.0D0+NU))
      KMOD=E/(3.0D0*(1.0D0-2.0D0*NU))
      DEN=3.0D0*G+HISO
      AA=MAX(0.0D0,1.0D0-3.0D0*G*DG/QTR)
      HR=HISO/DEN
      RR=SQRT(MAX(1.0D-40,2.0D0/3.0D0))*QTR
      M(1)=SDEV(1)/RR
      M(2)=SDEV(2)/RR
      M(3)=SDEV(3)/RR
      M(4)=SDEV(4)/RR
      M(5)=SDEV(5)/RR
      M(6)=SDEV(6)/RR
      COEF=2.0D0*G*(HR-AA)
C
      DO J=1,6
         DO I=1,6
            B(I)=0.0D0
         END DO
         IF (J.LE.3) THEN
            B(J)=1.0D0
         ELSE
C           Unit engineering shear corresponds to tensor shear 1/2.
            B(J)=0.5D0
         END IF
         TRB=B(1)+B(2)+B(3)
         DEV(1)=B(1)-TRB/3.0D0
         DEV(2)=B(2)-TRB/3.0D0
         DEV(3)=B(3)-TRB/3.0D0
         DEV(4)=B(4)
         DEV(5)=B(5)
         DEV(6)=B(6)
         MDOT=M(1)*B(1)+M(2)*B(2)+M(3)*B(3)+
     1        2.0D0*(M(4)*B(4)+M(5)*B(5)+M(6)*B(6))
         DS(1)=KMOD*TRB+2.0D0*G*AA*DEV(1)+COEF*M(1)*MDOT
         DS(2)=KMOD*TRB+2.0D0*G*AA*DEV(2)+COEF*M(2)*MDOT
         DS(3)=KMOD*TRB+2.0D0*G*AA*DEV(3)+COEF*M(3)*MDOT
         DS(4)=2.0D0*G*AA*DEV(4)+COEF*M(4)*MDOT
         DS(5)=2.0D0*G*AA*DEV(5)+COEF*M(5)*MDOT
         DS(6)=2.0D0*G*AA*DEV(6)+COEF*M(6)*MDOT
         DO I=1,6
            CALG(I,J)=DS(I)
         END DO
      END DO
      RETURN
      END
C=======================================================================
      SUBROUTINE KMATMUL6_Z31(A,B,C)
      IMPLICIT NONE
      DOUBLE PRECISION A(6,6),B(6,6),C(6,6)
      INTEGER I,J,K
      DO I=1,6
         DO J=1,6
            C(I,J)=0.0D0
            DO K=1,6
               C(I,J)=C(I,J)+A(I,K)*B(K,J)
            END DO
         END DO
      END DO
      RETURN
      END
C=======================================================================
      SUBROUTINE KEXPDMG_Z22(R,A,DMAX,D)
      IMPLICIT NONE
      DOUBLE PRECISION R,A,DMAX,D
      IF (R.LE.1.0D0) THEN
         D=0.0D0
      ELSE
         D=1.0D0-EXP(A*(1.0D0-R))/R
         D=MIN(DMAX,MAX(0.0D0,D))
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KMIXED_Z22(R,A,K,E,RF,DF,XT,XPO,DMAX,D)
      IMPLICIT NONE
      DOUBLE PRECISION R,A,K,E,RF,DF,XT,XPO,DMAX,D
      DOUBLE PRECISION RL,RE,DL
      IF (R.LE.1.0D0) THEN
         D=0.0D0
         RETURN
      END IF
      IF (RF.LE.1.0D0 .OR. XPO.LE.0.0D0) THEN
         CALL KEXPDMG_Z22(R,A,DMAX,D)
         RETURN
      END IF
      RL=MAX(1.0D0,MIN(R,RF))
      DL=1.0D0+K/E-(1.0D0+K/E)/RL
      DL=MAX(0.0D0,MIN(DMAX,DL))
      RE=MAX(1.0D0,(1.0D0-DF)*XT*R/XPO)
      D=1.0D0-(1.0D0-DL)*EXP(A*(1.0D0-RE))/RE
      D=MIN(DMAX,MAX(0.0D0,D))
      RETURN
      END
C=======================================================================
      SUBROUTINE KISO_Z22(E,NU,C)
      IMPLICIT NONE
      DOUBLE PRECISION E,NU,C(6,6),LAM,MU
      INTEGER I,J
      LAM=E*NU/((1.0D0+NU)*(1.0D0-2.0D0*NU))
      MU=E/(2.0D0*(1.0D0+NU))
      DO I=1,6
         DO J=1,6
            C(I,J)=0.0D0
         END DO
      END DO
      C(1,1)=LAM+2.0D0*MU
      C(2,2)=C(1,1)
      C(3,3)=C(1,1)
      C(1,2)=LAM
      C(1,3)=LAM
      C(2,1)=LAM
      C(2,3)=LAM
      C(3,1)=LAM
      C(3,2)=LAM
      C(4,4)=MU
      C(5,5)=MU
      C(6,6)=MU
      RETURN
      END
C=======================================================================
      SUBROUTINE KORTHO_Z22(E1,E2,E3,N12,N13,N23,
     1 G12,G13,G23,C)
      IMPLICIT NONE
      DOUBLE PRECISION E1,E2,E3,N12,N13,N23,G12,G13,G23
      DOUBLE PRECISION C(6,6),S(6,6)
      INTEGER I,J
      DO I=1,6
         DO J=1,6
            S(I,J)=0.0D0
         END DO
      END DO
      S(1,1)=1.0D0/E1
      S(2,2)=1.0D0/E2
      S(3,3)=1.0D0/E3
      S(1,2)=-N12/E1
      S(2,1)=S(1,2)
      S(1,3)=-N13/E1
      S(3,1)=S(1,3)
      S(2,3)=-N23/E2
      S(3,2)=S(2,3)
      S(4,4)=1.0D0/G12
      S(5,5)=1.0D0/G13
      S(6,6)=1.0D0/G23
      CALL KINV6_Z22(S,C)
      RETURN
      END
C=======================================================================
      SUBROUTINE KMATVEC6_Z22(A,X,Y)
      IMPLICIT NONE
      DOUBLE PRECISION A(6,6),X(6),Y(6)
      INTEGER I,J
      DO I=1,6
         Y(I)=0.0D0
         DO J=1,6
            Y(I)=Y(I)+A(I,J)*X(J)
         END DO
      END DO
      RETURN
      END
C=======================================================================
      SUBROUTINE KMISES_Z22(S,Q)
      IMPLICIT NONE
      DOUBLE PRECISION S(6),Q
      Q=SQRT(MAX(0.0D0,0.5D0*((S(1)-S(2))**2+
     1 (S(2)-S(3))**2+(S(3)-S(1))**2)+
     2 3.0D0*(S(4)**2+S(5)**2+S(6)**2)))
      RETURN
      END
C=======================================================================
      SUBROUTINE KINV6_Z22(A,AINV)
C     Gauss-Jordan inverse with partial pivoting.
      IMPLICIT NONE
      DOUBLE PRECISION A(6,6),AINV(6,6),W(6,12)
      DOUBLE PRECISION PIV,AMAX,TMP,FAC
      INTEGER I,J,K,IP
      DO I=1,6
         DO J=1,6
            W(I,J)=A(I,J)
            W(I,J+6)=0.0D0
         END DO
         W(I,I+6)=1.0D0
      END DO
      DO K=1,6
         IP=K
         AMAX=ABS(W(K,K))
         DO I=K+1,6
            IF (ABS(W(I,K)).GT.AMAX) THEN
               AMAX=ABS(W(I,K))
               IP=I
            END IF
         END DO
         IF (AMAX.LE.1.0D-30) THEN
            WRITE(7,*) 'Singular 6x6 compliance matrix.'
            CALL XIT
         END IF
         IF (IP.NE.K) THEN
            DO J=1,12
               TMP=W(K,J)
               W(K,J)=W(IP,J)
               W(IP,J)=TMP
            END DO
         END IF
         PIV=W(K,K)
         DO J=1,12
            W(K,J)=W(K,J)/PIV
         END DO
         DO I=1,6
            IF (I.NE.K) THEN
               FAC=W(I,K)
               DO J=1,12
                  W(I,J)=W(I,J)-FAC*W(K,J)
               END DO
            END IF
         END DO
      END DO
      DO I=1,6
         DO J=1,6
            AINV(I,J)=W(I,J+6)
         END DO
      END DO
      RETURN
      END
