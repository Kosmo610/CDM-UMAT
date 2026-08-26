C=======================================================================
C  UMAT_CSIC_RVE_DAMAGE_V2_7D.for
C
C  V2_7D = V2_7P + ONE diagnostic state variable in the yarn:
C              SDV17 = SHR1T, the shear share of the longitudinal
C                      tensile criterion Eq.11, latched at onset.
C          Eq.11 is
C              FI1T = sqrt((s11/XT)^2+(t12/S12)^2+(t13/S13)^2)
C          and SDV17 = [(t12/S12)^2+(t13/S13)^2] / FI1T^2, in [0,1]:
C              0 -> s11 alone drove that element to onset
C              1 -> shear alone did
C          It answers the open question of the temperature audit: our
C          yarn card carries XT=421 (a back-calibration) against shear
C          strengths of 120, so s11 dominates and the yarn sets the
C          strength; the paper's own XT=2835 would leave the s11 term
C          at (421/2835)^2 = 2.2 % and hand the mechanism to shear,
C          which is what the paper describes. Until now that split was
C          only INFERRED from a calibration regression (~69 % s11).
C          SDV17 measures it per integration point instead.
C
C          PHYSICALLY INERT. Nothing downstream reads SV(17): stress,
C          stiffness, damage and PNEWDT are bit-identical to V2_7P.
C          The write is guarded by NSTATV>=17, so every existing
C          16-depvar deck still runs -- it simply gets no diagnostic.
C          Meaningful only where SDV5 (=R1T) >= 1; elsewhere it stays
C          0, since an element that never initiated the 1T mode has no
C          initiating mechanism to report.
C
C          It must be added BEFORE the next batch, not after: *Depvar
C          fixes the slot count at job start, so attaching it later
C          would force every run to be repeated.
C
C  V2_7P = V2_7 with the STATEV layout rearranged so the default Abaqus
C          labels match Zhang 2022's figures:
C              SDV1  = yarn longitudinal damage
C              SDV2  = yarn transverse damage
C              SDV14 = matrix damage
C          NUMERICALLY IDENTICAL to V2_7 -- no equation, criterion or
C          material response is touched. Storage only:
C            yarn   SV(2) <-> SV(3)   (D1C and DTT swap slots so the
C                                      transverse tensile damage lands
C                                      on SDV2 like the paper)
C            matrix SV(14) = mirror of SV(1) (=DMT), written last so
C                            nothing overwrites it.
C          NSTATV IS UNCHANGED (matrix 14, yarn 16) -- no deck needs a
C          larger *Depvar. The V2_7 diagnostic that used matrix slot 14
C          (RFAC at the largest damage jump) is dropped; no extraction
C          script reads it.
C          Decks paired with this file should carry *Depvar blocks with
C          NO name lines so fields display as SDV1/SDV2/SDV14 exactly
C          like the paper. Existing odbs keep their SDV_DMT-style names.
C
C  3-D damage UMAT for C/SiC plain-weave manufacturing cooldown RVE.
C
C  Material branches selected by CMNAME:
C    CSIC_YARN_DAMAGE  : orthotropic yarn, 3-D Hashin-type initiation
C                        and exponential irreversible damage.
C    SIC_MATRIX_DAMAGE : isotropic brittle matrix, principal-stress
C                        initiation, tension/compression split, and
C                        crack-closure-aware active stiffness.
C
C  V2_7 = V2_6 + audit fixes (no behavior change for any card used in
C         a completed run):
C         (a) MCRIT>=0.5 smooth band: the tension/compression partition
C             weights are now renormalized so the dominant branch keeps
C             the full paper criterion. The V2_5/V2_6 partition diluted
C             BOTH branches inside |I1|<0.1*Xc (at I1=0 each was
C             0.5*Q/X, i.e. damage onset needed twice the paper
C             stress). Outside the band, and in the BAND->0 limit,
C             identical to before. MCRIT<0.5 paths are untouched.
C         (b) Yarn PROPS(32)=GF1T sanity guard (negative, or >0.5 N/mm
C             which indicates card aliasing, now XITs with a message
C             instead of silently producing a near-flat softening law).
C         (c) Stale V2_1/V2_2 version strings in messages updated.
C
C  V2_6 = V2_5 + yarn LONGITUDINAL crack-band regularization:
C         PROPS(32)=GF1T (N/mm). Absent or <=0 -> V2_5 exact. With
C         GF1T>0, A1TEFF = 2*g0*le/(GF1T-g0*le), g0=XT^2/(2*E1), the
C         same construction as matrix PROPS(16), so dissipated energy
C         integrates to GF1T/le and results stop depending on element
C         size. Motivated by the failed ETA convergence study
C         (peak 160.5/154.6/147.7 MPa at eta 1.0/0.5/0.25x).
C
C  V2_5 = V2_4 + PROPS(24)=MCRIT matrix criterion selector:
C         MCRIT>=0.5 reproduces paper Eq.15/16 verbatim (von Mises on
C         both sides of I1, no sqrt(3)); MCRIT<0.5 or absent keeps the
C         V2_4 Rankine/mixed path unchanged.
C
C  V2_4 = V2_3 + convergence fix for the matrix branch:
C         PROPS(23)=WTLAG lags the stress-state weight by one increment
C         so the secant Jacobian is consistent, and the I1 gate of V2_3
C         is applied through a smooth band instead of a hard switch.
C
C  V2_3 = V2_2 + first-invariant gate on the matrix compressive
C         criterion (paper Eq.16). See PROPS(22)=I1GATE below.
C
C  V2_2 = MERGE OF THE TWO V2_1 LINEAGES:
C   Lineage A (physics):
C    (1) Weibull strength field: if PROPS(17)=m>0 each element samples
C        a tensile strength XTE from a Weibull distribution whose MEAN
C        equals PROPS(4). Deterministic hash of integration-point
C        coordinates (reproducible, mesh-tied). Frozen in SDV9.
C        PROPS(18)=seed. Sources: Zhang 2022 Ceram.Int.48 Table 2
C        (310 MPa) and Yang 2017 JECS Table 2 (Weibull modulus 5.1).
C    (2) Crack-band regularization: if PROPS(16)=Gf>0 (N/mm) the
C        tensile softening factor per element is
C           g0 = XTE^2/(2E),  A_eff = 2*g0*le/(Gf - g0*le)
C        so the dissipated energy density integrates to Gf/le
C        (mesh-objective). Snap-back clamp 50. Stored in SDV10.
C   Lineage B (numerical controls):
C    (3) Cutback shaping: matrix PROPS(19-21) = yarn PROPS(29-31) =
C        cut_trigger (margin on max_djump before any cutback),
C        cut_safety (target fraction of max_djump after the cut),
C        cut_max_factor (cap on the requested PNEWDT so cuts are
C        decisive; 0 disables the cap). Defaults 1.0/1.0/0.0
C        reproduce V2_1 behavior exactly.
C    (4) Diagnostic SDVs: matrix 11-14 = max damage jump / min
C        requested PNEWDT / temperature at max jump / criterion at
C        max jump. Yarn 13-16 likewise.
C   Safety:
C    (5) KGUARD sanity check XITs with a clear message when PROPS
C        16-18 look like a V2_1-lineage cutback card (e.g. Gf>0.5
C        N/mm or 0<m<2) to prevent silent parameter aliasing.
C   Compatibility:
C    (6) Matrix NPROPS=15 -> V2_0 exact. NPROPS=18 with NSTATV>=10 ->
C        lineage-A V2_1 exact. NPROPS>=19 requires NSTATV>=14.
C        Yarn NPROPS=28 -> V2_0/V2_1 exact. NPROPS>=29 requires
C        NSTATV>=16.
C
C   V2_3 addition:
C    (7) PROPS(22)=I1GATE for the SIC_MATRIX_DAMAGE branch.
C        Zhang 2022 (Ceram.Int.48) Eq.15/16 admit the Mises-type matrix
C        criteria only on the matching side of the hydrostatic axis:
C        tension for I1>=0, compression for I1<=0. V2_2 evaluated the
C        compressive branch unconditionally, so a purely tensile state
C        (I1>0) still produced "compressive" damage once
C        Q > sqrt(3)*Xc. During RVE cooldown the matrix sits in
C        triaxial tension (I1>0), so that damage was spurious.
C          I1GATE = 0 : legacy V2_2 behaviour (no gate)
C                 = 1 : gate the Mises term only (DEFAULT). A genuine
C                       local-compression check on the minimum
C                       principal stress is retained.
C                 = 2 : paper Eq.16 exactly (FIC=0 while I1>0)
C        Omitting PROPS(22) (NPROPS<22) selects I1GATE=1.
C
C   V2_4 additions:
C    (8) PROPS(23)=WTLAG (SIC_MATRIX_DAMAGE branch).
C        DACT = 1-(1-FT*dt)(1-FC*dc) with FT,FC built from the
C        stress-state weight WT, which is a function of the CURRENT
C        strain. The returned Jacobian is the secant (1-DACT)*C0 and
C        does not differentiate that dependence. The mismatch leaves a
C        residual floor that does NOT shrink when DTIME is cut: with
C        DTIME -> 0 the viscous factor GAM = DTIME/(ETA+DTIME) freezes
C        the damage variables, yet DACT keeps moving through WT, so
C        Newton stalls and Abaqus cuts back to the minimum increment.
C        Observed in the V2_3 cooldown at 260 C, where many principal
C        stresses cross zero as the yarn transverse stress changes sign
C        and WT swings between 0 and 1.
C          WTLAG = 0 : use the current WT (legacy V2_2/V2_3)
C                = 1 : use the last converged WT from SDV6 (DEFAULT).
C                      DACT then depends only on the damage state, which
C                      IS frozen as DTIME -> 0, restoring a consistent
C                      secant Jacobian. The crack-closure model is kept,
C                      lagged by one increment.
C        Omitting PROPS(23) (NPROPS<23) selects WTLAG=1.
C    (9) The PROPS(22) I1 gate now ramps smoothly over |I1| <= 0.1*Xc
C        instead of switching discontinuously at I1=0.
C
C  IMPORTANT:
C  - Designed for the manufacturing-cooling RVE (Step 1 = cooldown).
C  - Thermal strain is supplied by Abaqus *EXPANSION. STRAN and DSTRAN
C    passed to UMAT are therefore mechanical strains.
C  - The Jacobian is a symmetric damaged-secant stiffness. Small
C    viscous regularization and automatic cutback improve robustness.
C  - Weibull applies to matrix TENSION only. Compression and the yarn
C    strengths remain deterministic.
C  - dmax_t < 1 keeps a residual stiffness; the Gf calibration is
C    exact in the limit dmax_t -> 1.
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
      DOUBLE PRECISION EPS(6),SOLD(6),SSEOLD,SPDOLD,WORK,DW
      INTEGER I,J,NSVREQ
C
      IF (NTENS.NE.6 .OR. NDI.NE.3 .OR. NSHR.NE.3) THEN
         WRITE(7,*) 'UMAT_CSIC_RVE_DAMAGE_V2_7D: 3-D solids only.'
         WRITE(7,*) 'NOEL,NPT,NDI,NSHR,NTENS=',NOEL,NPT,NDI,NSHR,
     1                NTENS
         CALL XIT
      END IF
C
      DO I=1,6
         EPS(I)=STRAN(I)+DSTRAN(I)
         SOLD(I)=STRESS(I)
         DDSDDT(I)=0.0D0
         DRPLDE(I)=0.0D0
         DO J=1,6
            DDSDDE(I,J)=0.0D0
         END DO
      END DO
      SSEOLD=SSE
      SPDOLD=SPD
      SCD=0.0D0
      RPL=0.0D0
      DRPLDT=0.0D0
      IF (PNEWDT.LE.0.0D0) PNEWDT=1.0D0
C
      IF (INDEX(CMNAME,'YARN').GT.0) THEN
         NSVREQ=12
         IF (NPROPS.GE.29) NSVREQ=16
         IF (NPROPS.LT.28 .OR. NSTATV.LT.NSVREQ) THEN
            WRITE(7,*) 'YARN requires NPROPS>=28 with NSTATV>=12'
            WRITE(7,*) 'or NPROPS>=29 with NSTATV>=16 (V2_2 card;'
            WRITE(7,*) 'optional PROPS(32)=GF1T is the V2_6 card).'
            CALL XIT
         END IF
C        NSVREQ stays 16 on purpose: SDV17 is a diagnostic, so a deck
C        that declares only 16 must keep running. KYARN_UPDATE gets
C        NSTATV and writes SV(17) only when the deck asked for it.
         CALL KYARN_UPDATE(EPS,STRESS,DDSDDE,STATEV,PROPS,
     1        NPROPS,NSTATV,DTIME,TEMP,DTEMP,PNEWDT,KSTEP,CELENT)
      ELSE IF (INDEX(CMNAME,'MATRIX').GT.0) THEN
         NSVREQ=8
         IF (NPROPS.GE.16) NSVREQ=10
         IF (NPROPS.GE.19) NSVREQ=14
         IF (NPROPS.LT.15 .OR. NSTATV.LT.NSVREQ) THEN
            WRITE(7,*) 'MATRIX requires NPROPS>=15 (V2_0 card) or'
            WRITE(7,*) 'NPROPS>=16 with NSTATV>=10 (V2_1 card) or'
            WRITE(7,*) 'NPROPS>=19 with NSTATV>=14 (V2_2 card).'
            CALL XIT
         END IF
         CALL KMATRIX_UPDATE(EPS,STRESS,DDSDDE,STATEV,PROPS,
     1        NPROPS,DTIME,TEMP,DTEMP,PNEWDT,KSTEP,CELENT,COORDS)
      ELSE
         WRITE(7,*) 'Unknown CMNAME in UMAT: ',CMNAME
         CALL XIT
      END IF
C
C     Approximate energetic bookkeeping for diagnostics.
      WORK=0.0D0
      SSE=0.0D0
      DO I=1,6
         WORK=WORK+0.5D0*(SOLD(I)+STRESS(I))*DSTRAN(I)
         SSE=SSE+0.5D0*STRESS(I)*EPS(I)
      END DO
      DW=WORK-(SSE-SSEOLD)
      SPD=MAX(SPDOLD,SPDOLD+MAX(0.0D0,DW))
      RETURN
      END
C=======================================================================
      SUBROUTINE KYARN_UPDATE(EPS,STRESS,CTAN,SV,P,NP,NSV,DTIME,TEMP,
     1 DTEMP,PNEWDT,KSTEP,CELENT)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT
      DOUBLE PRECISION C0(6,6),CD(6,6),SE(6),RSC(6)
      DOUBLE PRECISION E1,E2,E3,NU12,NU13,NU23,G12,G13,G23
      DOUBLE PRECISION XT,XC,YT,YC,S12,S13,S23
      DOUBLE PRECISION A1T,A1C,ATT,ATC,DMAX1,DMAXT,ETA,DJMAX
      DOUBLE PRECISION PMIN,ENABLE,FREEZESTEP
      DOUBLE PRECISION CUTTRG,CUTSAF,CUTMXF,REQ,CREQ
      DOUBLE PRECISION FI1T,FI1C,FITT,FITC,SUMT,TERM
      DOUBLE PRECISION R1T,R1C,RTT,RTC,TAR,GAM
      DOUBLE PRECISION D1T0,D1C0,DTT0,DTC0,D1T,D1C,DTT,DTC
      DOUBLE PRECISION D1,DT,DS12,DS13,DS23,DJ,TEND,RFAC
      DOUBLE PRECISION GF1T,A1TEFF,G01,GLE1
      DOUBLE PRECISION R1TOLD,SHRNUM
      INTEGER I,J,KSTEP,MODE,NP,NSV
C
      E1=P(2)
      E2=P(3)
      E3=P(4)
      NU12=P(5)
      NU13=P(6)
      NU23=P(7)
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
      ATT=P(20)
      ATC=P(21)
      DMAX1=P(22)
      DMAXT=P(23)
      ETA=P(24)
      DJMAX=P(25)
      FREEZESTEP=P(26)
      PMIN=P(27)
      ENABLE=P(28)
C ---- V2_2 optional cutback shaping (defaults = V2_1 behavior) --------
      CUTTRG=1.0D0
      CUTSAF=1.0D0
      CUTMXF=0.0D0
      IF (NP.GE.29) CUTTRG=MAX(1.0D0,P(29))
      IF (NP.GE.30) CUTSAF=P(30)
      IF (NP.GE.31) CUTMXF=P(31)
C ---- V2_6: PROPS(32)=GF1T, yarn LONGITUDINAL tensile fracture energy.
C     Absent or <=0 -> A1T is used directly, i.e. V2_5 behaviour, so
C     every existing 31-constant card is unaffected.
C
C     With GF1T>0 the softening exponent is rebuilt per element as
C         A1TEFF = 2*g0*le/(GF1T-g0*le),   g0 = XT^2/(2*E1)
C     which is the same crack-band construction already used for the
C     matrix (PROPS 16). It makes the energy dissipated by longitudinal
C     yarn softening integrate to GF1T/le, so the result stops depending
C     on element size. Without it the softening band collapses onto one
C     element and both the mesh study and the viscosity (ETA) study fail
C     to converge - which is exactly what was measured:
C       ETA 1.00x/0.50x/0.25x gave peak 160.5/154.6/147.7 MPa
C       (-3.70%, -4.45%: the step GREW, so there was no limit).
      GF1T=0.0D0
      IF (NP.GE.32) GF1T=P(32)
C ---- V2_7: sanity guard. GF1T=0 legitimately disables the crack band,
C     but a negative value, or one above 0.5 N/mm (yarn g0*le is about
C     0.02-0.04 N/mm here, and an aliased A-exponent like 2.0 would land
C     far above), silently yields a near-flat softening law. Fail hard.
      IF (GF1T.LT.0.0D0 .OR. GF1T.GT.0.5D0) THEN
         WRITE(7,*) 'YARN PROPS(32)=GF1T out of range: ',GF1T
         WRITE(7,*) 'Expected 0 (off) or 0<GF1T<=0.5 N/mm.'
         WRITE(7,*) 'A softening exponent (e.g. 2.0) was likely'
         WRITE(7,*) 'placed at position 32. Fix the material card.'
         CALL XIT
      END IF
C
      CALL KORTHO(E1,E2,E3,NU12,NU13,NU23,G12,G13,G23,C0)
      CALL KMATVEC6(C0,EPS,SE)
C
C     Effective-stress 3-D Hashin-type criteria in yarn material axes.
      FI1T=0.0D0
      FI1C=0.0D0
      FITT=0.0D0
      FITC=0.0D0
      IF (SE(1).GE.0.0D0) THEN
         FI1T=SQRT((SE(1)/XT)**2+(SE(4)/S12)**2+
     1              (SE(5)/S13)**2)
      ELSE
         FI1C=ABS(SE(1))/XC
      END IF
      SUMT=SE(2)+SE(3)
      IF (SUMT.GE.0.0D0) THEN
         TERM=(SUMT/YT)**2+(SE(6)*SE(6)-SE(2)*SE(3))/
     1        (S23*S23)+(SE(4)/S12)**2+(SE(5)/S13)**2
         FITT=SQRT(MAX(0.0D0,TERM))
      ELSE
         TERM=((YC/(2.0D0*S23))**2-1.0D0)*SUMT/YC+
     1        (SUMT/(2.0D0*S23))**2+
     2        (SE(6)*SE(6)-SE(2)*SE(3))/(S23*S23)+
     3        (SE(4)/S12)**2+(SE(5)/S13)**2
         FITC=SQRT(MAX(0.0D0,TERM))
      END IF
C
C ---- V2_6: element-size-objective longitudinal softening exponent ---
      IF (GF1T.GT.0.0D0) THEN
         G01=XT*XT/(2.0D0*E1)
         GLE1=G01*CELENT
         IF (GF1T.GT.1.02D0*GLE1) THEN
            A1TEFF=2.0D0*GLE1/(GF1T-GLE1)
         ELSE
            A1TEFF=50.0D0
         END IF
         A1TEFF=MIN(50.0D0,MAX(1.0D-2,A1TEFF))
      ELSE
         A1TEFF=A1T
      END IF
C
      D1T0=MAX(0.0D0,MIN(DMAX1,SV(1)))
      D1C0=MAX(0.0D0,MIN(DMAX1,SV(3)))
      DTT0=MAX(0.0D0,MIN(DMAXT,SV(2)))
      DTC0=MAX(0.0D0,MIN(DMAXT,SV(4)))
C     R1TOLD is kept so the V2_7D onset latch below can ask "was this
C     element below 1 last increment?" after SV(5) has been rewritten.
      R1TOLD=SV(5)
      R1T=MAX(R1TOLD,FI1T)
      R1C=MAX(SV(6),FI1C)
      RTT=MAX(SV(7),FITT)
      RTC=MAX(SV(8),FITC)
      D1T=D1T0
      D1C=D1C0
      DTT=DTT0
      DTC=DTC0
C
      IF (ENABLE.GT.0.5D0 .AND. DBLE(KSTEP).LE.FREEZESTEP) THEN
         IF (ETA.GT.0.0D0) THEN
            GAM=DTIME/(ETA+DTIME)
         ELSE
            GAM=1.0D0
         END IF
         CALL KDAMAGE_TARGET(R1T,A1TEFF,DMAX1,TAR)
         D1T=MAX(D1T0,D1T0+GAM*(TAR-D1T0))
         CALL KDAMAGE_TARGET(R1C,A1C,DMAX1,TAR)
         D1C=MAX(D1C0,D1C0+GAM*(TAR-D1C0))
         CALL KDAMAGE_TARGET(RTT,ATT,DMAXT,TAR)
         DTT=MAX(DTT0,DTT0+GAM*(TAR-DTT0))
         CALL KDAMAGE_TARGET(RTC,ATC,DMAXT,TAR)
         DTC=MAX(DTC0,DTC0+GAM*(TAR-DTC0))
      END IF
C
      D1=1.0D0-(1.0D0-D1T)*(1.0D0-D1C)
      DT=1.0D0-(1.0D0-DTT)*(1.0D0-DTC)
      D1=MIN(0.999D0,MAX(0.0D0,D1))
      DT=MIN(0.999D0,MAX(0.0D0,DT))
      DS12=1.0D0-SQRT((1.0D0-D1)*(1.0D0-DT))
      DS13=DS12
      DS23=DT
C
C     Symmetric positive-definite degradation: Cd = R*C0*R.
      RSC(1)=SQRT(1.0D0-D1)
      RSC(2)=SQRT(1.0D0-DT)
      RSC(3)=SQRT(1.0D0-DT)
      RSC(4)=SQRT(1.0D0-DS12)
      RSC(5)=SQRT(1.0D0-DS13)
      RSC(6)=SQRT(1.0D0-DS23)
      DO I=1,6
         DO J=1,6
            CD(I,J)=RSC(I)*C0(I,J)*RSC(J)
            CTAN(I,J)=CD(I,J)
         END DO
      END DO
      CALL KMATVEC6(CD,EPS,STRESS)
C
      MODE=1
      RFAC=R1T
      IF (R1C.GT.RFAC) THEN
         MODE=2
         RFAC=R1C
      END IF
      IF (RTT.GT.RFAC) THEN
         MODE=3
         RFAC=RTT
      END IF
      IF (RTC.GT.RFAC) THEN
         MODE=4
         RFAC=RTC
      END IF
      TEND=TEMP+DTEMP
      IF (SV(12).EQ.0.0D0 .AND. RFAC.GE.1.0D0) SV(12)=TEND
C
      SV(1)=D1T
      SV(3)=D1C
      SV(2)=DTT
      SV(4)=DTC
      SV(5)=R1T
      SV(6)=R1C
      SV(7)=RTT
      SV(8)=RTC
      SV(9)=D1
      SV(10)=DT
      SV(11)=DBLE(MODE)
C
C ---- V2_7D diagnostic: which term of Eq.11 killed this point --------
C     SHR1T = [(t12/S12)^2+(t13/S13)^2] / FI1T^2, in [0,1].
C       0 -> s11 alone drove it to onset;  1 -> shear alone did.
C     Latched ONCE, on the increment where the 1T mode initiates
C     (R1T crosses 1), so it reports the INITIATING mechanism rather
C     than whatever the stress state happens to be later.
C     PHYSICALLY INERT -- SV(17) is never read back, so stress,
C     stiffness, damage and PNEWDT are bit-identical to V2_7P.
C     Guarded by NSV>=17: a deck that still declares *Depvar 16 runs
C     unchanged and simply carries no diagnostic. FI1T>=1 makes the
C     division safe, and SE(1)<0 leaves FI1T=0 so compression never
C     reaches here.
      IF (NSV.GE.17 .AND. R1TOLD.LT.1.0D0 .AND. FI1T.GE.1.0D0) THEN
         SHRNUM=(SE(4)/S12)**2+(SE(5)/S13)**2
         SV(17)=MIN(1.0D0,MAX(0.0D0,SHRNUM/(FI1T*FI1T)))
      END IF
C
      DJ=MAX(ABS(D1T-D1T0),ABS(D1C-D1C0),
     1       ABS(DTT-DTT0),ABS(DTC-DTC0))
      IF (DJMAX.GT.0.0D0 .AND. DJ.GT.CUTTRG*DJMAX) THEN
         REQ=CUTSAF*DJMAX/DJ
         IF (CUTMXF.GT.0.0D0) REQ=MIN(REQ,CUTMXF)
         REQ=MAX(PMIN,REQ)
         PNEWDT=MIN(PNEWDT,REQ)
         IF (NP.GE.29) THEN
            CREQ=SV(14)
            IF (CREQ.LE.0.0D0) CREQ=1.0D0
            SV(14)=MIN(CREQ,REQ)
         END IF
      END IF
      IF (NP.GE.29 .AND. DJ.GT.SV(13)) THEN
         SV(13)=DJ
         SV(15)=TEND
         SV(16)=RFAC
      END IF
      RETURN
      END
C=======================================================================
      SUBROUTINE KMATRIX_UPDATE(EPS,STRESS,CTAN,SV,P,NP,DTIME,
     1 TEMP,DTEMP,PNEWDT,KSTEP,CELENT,COORDS)
      IMPLICIT NONE
      DOUBLE PRECISION EPS(6),STRESS(6),CTAN(6,6),SV(*),P(*)
      DOUBLE PRECISION DTIME,TEMP,DTEMP,PNEWDT,CELENT,COORDS(3)
      DOUBLE PRECISION C0(6,6),SE(6),EV(3)
      DOUBLE PRECISION E,NU,XT,XC,AT,AC,DMAXT,DMAXC,ETA,DJMAX
      DOUBLE PRECISION FREEZESTEP,CLOSURE,PMIN,ENABLE
      DOUBLE PRECISION GFT,WEIBM,SEED,XTE,ATEFF,U,SIG0,G0,GLE
      DOUBLE PRECISION CUTTRG,CUTSAF,CUTMXF,REQ,CREQ
      DOUBLE PRECISION FIT,FIC,RT,RC,DT0,DC0,DTN,DCN,TAR,GAM
      DOUBLE PRECISION WT,DEN,FT,FC,DACT,Q,DJ,TEND,RFAC
      DOUBLE PRECISION TRI,I1GATE,FICM,FICP,GW,BAND
      DOUBLE PRECISION WTLAG,WTU,MCRIT,WNORM
      INTEGER I,J,KSTEP,MODE,NP,IER
C
      E=P(2)
      NU=P(3)
      XT=P(4)
      XC=P(5)
      AT=P(6)
      AC=P(7)
      DMAXT=P(8)
      DMAXC=P(9)
      ETA=P(10)
      DJMAX=P(11)
      FREEZESTEP=P(12)
      CLOSURE=P(13)
      PMIN=P(14)
      ENABLE=P(15)
C ---- V2_1 optional block (defaults reproduce V2_0 behavior) ----------
      GFT=0.0D0
      WEIBM=0.0D0
      SEED=0.0D0
      IF (NP.GE.16) GFT=P(16)
      IF (NP.GE.17) WEIBM=P(17)
      IF (NP.GE.18) SEED=P(18)
C ---- V2_2 optional cutback shaping (defaults = V2_1 behavior) --------
      CUTTRG=1.0D0
      CUTSAF=1.0D0
      CUTMXF=0.0D0
      IF (NP.GE.19) CUTTRG=MAX(1.0D0,P(19))
      IF (NP.GE.20) CUTSAF=P(20)
      IF (NP.GE.21) CUTMXF=P(21)
C ---- V2_3 optional first-invariant gate (default = gate Mises term) --
      I1GATE=1.0D0
      IF (NP.GE.22) I1GATE=P(22)
C ---- V2_4 optional lagged stress-state weight (default = on) ---------
      WTLAG=1.0D0
      IF (NP.GE.23) WTLAG=P(23)
C ---- V2_5: PROPS(24)=MCRIT selects the matrix failure criterion.
C       MCRIT<0.5 (or absent)  -> V2_4 behaviour, unchanged:
C           tension     = Rankine, max principal / Xt, no I1 gate
C           compression = max(max-principal, Mises/(sqrt3*Xc)), I1 gated
C       MCRIT>=0.5             -> Zhang 2022 Eq.15/16 verbatim:
C           both branches use the von Mises equivalent effective stress
C           and are separated ONLY by the sign of I1, with no sqrt(3).
C       The paper switches hard at I1=0. A hard switch is a
C       discontinuity in the constitutive law, so the same smooth
C       +/-BAND ramp introduced in V2_4 is reused to partition the two
C       branches; BAND->0 recovers the paper exactly.
      MCRIT=0.0D0
      IF (NP.GE.24) MCRIT=P(24)
C ---- V2_2 sanity guard against V2_1-lineage card aliasing ------------
      IF (NP.GE.16) THEN
         CALL KGUARD(GFT,WEIBM,IER)
         IF (IER.NE.0) THEN
            WRITE(7,*) 'MATRIX PROPS sanity check failed. IERR=',IER
            WRITE(7,*) 'V2_2 semantics: P16=Gf(N/mm)<=0.5,'
            WRITE(7,*) 'P17=Weibull m (0 or >=2), P18=seed,'
            WRITE(7,*) 'P19-21=cut trigger/safety/max factor.'
            WRITE(7,*) 'A V2_1-lineage card (P16=cut_trigger) was'
            WRITE(7,*) 'likely supplied. Fix the *USER MATERIAL card.'
            CALL XIT
         END IF
      END IF
C
C ---- V2_1 (1): per-element Weibull tensile strength ------------------
C     Sampled once from a deterministic coordinate hash, frozen in SV9.
C     P(4) is interpreted as the MEAN strength when WEIBM>0.
      IF (WEIBM.GT.0.0D0) THEN
         XTE=SV(9)
         IF (XTE.LE.0.0D0) THEN
            CALL KHASH01(COORDS,SEED,U)
            SIG0=XT/GAMMA(1.0D0+1.0D0/WEIBM)
            XTE=SIG0*(-LOG(1.0D0-U))**(1.0D0/WEIBM)
         END IF
      ELSE
         XTE=XT
      END IF
C
C ---- V2_1 (2): crack-band tensile softening factor -------------------
C     A_eff = 2*g0*le/(Gf-g0*le) makes the dissipated energy density
C     integrate to Gf/le. Clamped to 50 when snap-back would occur.
      IF (GFT.GT.0.0D0) THEN
         G0=XTE*XTE/(2.0D0*E)
         GLE=G0*CELENT
         IF (GFT.GT.1.02D0*GLE) THEN
            ATEFF=2.0D0*GLE/(GFT-GLE)
         ELSE
            ATEFF=50.0D0
         END IF
         ATEFF=MIN(50.0D0,MAX(1.0D-2,ATEFF))
      ELSE
         ATEFF=AT
      END IF
C
      CALL KISO(E,NU,C0)
      CALL KMATVEC6(C0,EPS,SE)
      CALL KPRINC(SE,EV)
C
      CALL KMISES(SE,Q)
      TRI=SE(1)+SE(2)+SE(3)
      BAND=0.1D0*XC
      IF (MCRIT.GE.0.5D0) THEN
C ---- V2_5: paper Eq.15 (I1>=0) and Eq.16 (I1<=0), both von Mises ----
C     V2_7 fix: normalize the partition by its dominant weight. The
C     V2_5/V2_6 form FIT=(1-GW)*Q/XTE, FIC=GW*Q/XC diluted both
C     branches inside the smooth band (at I1=0 each was 0.5*Q/X, so
C     onset needed twice the paper stress). Dividing by
C     WNORM=max(GW,1-GW) keeps the dominant branch at the full paper
C     criterion at every I1, stays continuous across the band, and is
C     unchanged outside it (GW=0 or 1 gives WNORM=1).
         GW=0.5D0*(1.0D0-TRI/BAND)
         GW=MIN(1.0D0,MAX(0.0D0,GW))
         WNORM=MAX(GW,1.0D0-GW)
         FIT=((1.0D0-GW)/WNORM)*Q/XTE
         FIC=(GW/WNORM)*Q/XC
      ELSE
C ---- V2_4 path: Rankine tension, mixed compressive criterion --------
      FIT=MAX(0.0D0,EV(3))/XTE
      FICM=Q/(1.732050807568877D0*XC)
      FICP=MAX(0.0D0,-EV(1))/XC
      IF (I1GATE.LT.0.5D0) THEN
         GW=1.0D0
      ELSE
         GW=0.5D0*(1.0D0-TRI/BAND)
         GW=MIN(1.0D0,MAX(0.0D0,GW))
      END IF
      IF (I1GATE.GE.1.5D0) THEN
         FIC=GW*MAX(FICP,FICM)
      ELSE
         FIC=MAX(FICP,GW*FICM)
      END IF
      END IF
      DT0=MAX(0.0D0,MIN(DMAXT,SV(1)))
      DC0=MAX(0.0D0,MIN(DMAXC,SV(2)))
      RT=MAX(SV(3),FIT)
      RC=MAX(SV(4),FIC)
      DTN=DT0
      DCN=DC0
      IF (ENABLE.GT.0.5D0 .AND. DBLE(KSTEP).LE.FREEZESTEP) THEN
         IF (ETA.GT.0.0D0) THEN
            GAM=DTIME/(ETA+DTIME)
         ELSE
            GAM=1.0D0
         END IF
         CALL KDAMAGE_TARGET(RT,ATEFF,DMAXT,TAR)
         DTN=MAX(DT0,DT0+GAM*(TAR-DT0))
         CALL KDAMAGE_TARGET(RC,AC,DMAXC,TAR)
         DCN=MAX(DC0,DC0+GAM*(TAR-DC0))
      END IF
C
C     Stress-state weighting gives partial stiffness recovery on
C     crack closure.
      DEN=EV(1)*EV(1)+EV(2)*EV(2)+EV(3)*EV(3)
      IF (DEN.GT.1.0D-30) THEN
         WT=(MAX(EV(1),0.0D0)**2+MAX(EV(2),0.0D0)**2+
     1       MAX(EV(3),0.0D0)**2)/DEN
      ELSE
         WT=0.0D0
      END IF
      WT=MIN(1.0D0,MAX(0.0D0,WT))
      CLOSURE=MIN(1.0D0,MAX(0.0D0,CLOSURE))
C ---- V2_4: use the last converged WT so CTAN stays consistent --------
C     SV(6) still receives the freshly computed WT below, so the weight
C     is updated every increment and only lags by one.
      IF (WTLAG.GT.0.5D0) THEN
         WTU=MIN(1.0D0,MAX(0.0D0,SV(6)))
      ELSE
         WTU=WT
      END IF
      FT=CLOSURE+(1.0D0-CLOSURE)*WTU
      FC=1.0D0-WTU
      DACT=1.0D0-(1.0D0-FT*DTN)*(1.0D0-FC*DCN)
      DACT=MIN(0.999D0,MAX(0.0D0,DACT))
      DO I=1,6
         DO J=1,6
            CTAN(I,J)=(1.0D0-DACT)*C0(I,J)
         END DO
      END DO
      CALL KMATVEC6(CTAN,EPS,STRESS)
C
      MODE=1
      RFAC=RT
      IF (RC.GT.RFAC) THEN
         MODE=2
         RFAC=RC
      END IF
      TEND=TEMP+DTEMP
      IF (SV(8).EQ.0.0D0 .AND. RFAC.GE.1.0D0) SV(8)=TEND
      SV(1)=DTN
      SV(2)=DCN
      SV(3)=RT
      SV(4)=RC
      SV(5)=DACT
      SV(6)=WT
      SV(7)=DBLE(MODE)
C ---- V2_1 state (only when the extended card is in use) --------------
      IF (NP.GE.16) THEN
         SV(9)=XTE
         SV(10)=ATEFF
      END IF
C
      DJ=MAX(ABS(DTN-DT0),ABS(DCN-DC0))
      IF (DJMAX.GT.0.0D0 .AND. DJ.GT.CUTTRG*DJMAX) THEN
         REQ=CUTSAF*DJMAX/DJ
         IF (CUTMXF.GT.0.0D0) REQ=MIN(REQ,CUTMXF)
         REQ=MAX(PMIN,REQ)
         PNEWDT=MIN(PNEWDT,REQ)
         IF (NP.GE.19) THEN
            CREQ=SV(12)
            IF (CREQ.LE.0.0D0) CREQ=1.0D0
            SV(12)=MIN(CREQ,REQ)
         END IF
      END IF
      IF (NP.GE.19 .AND. DJ.GT.SV(11)) THEN
         SV(11)=DJ
         SV(13)=TEND
      END IF
C     V2_7P: SV(14) mirrors SV(1) so the paper's SDV14 label shows the
C     matrix damage. Written last so no later block overwrites it, and
C     unconditionally so it stays valid while damage is frozen (DTN
C     defaults to DT0). Slot count is unchanged.
      SV(14)=DTN
      RETURN
      END
C=======================================================================
      SUBROUTINE KGUARD(GFT,WEIBM,IERR)
C     Sanity check preventing silent V2_1-lineage PROPS aliasing.
C     IERR=1 Gf negative / 2 Gf>0.5 N/mm (SiC-matrix scale exceeded;
C     a cut_trigger value like 1.15 lands here) / 3 Weibull modulus
C     below 2 (a cut_safety value like 0.75 lands here) / 4 Weibull
C     modulus above 50.
      IMPLICIT NONE
      DOUBLE PRECISION GFT,WEIBM
      INTEGER IERR
      IERR=0
      IF (GFT.LT.0.0D0) IERR=1
      IF (GFT.GT.0.5D0) IERR=2
      IF (WEIBM.GT.0.0D0 .AND. WEIBM.LT.2.0D0) IERR=3
      IF (WEIBM.GT.50.0D0) IERR=4
      RETURN
      END
C=======================================================================
      SUBROUTINE KHASH01(C,SEED,U)
C     Deterministic coordinate hash -> uniform variate in (0,1).
C     Clamped to [1E-4, 1-1E-4] to exclude pathological Weibull tails.
      IMPLICIT NONE
      DOUBLE PRECISION C(3),SEED,U,ARG,H
      ARG=12.9898D0*C(1)+78.2330D0*C(2)+37.7190D0*C(3)
     1    +0.5453D0*SEED+0.1140D0
      H=SIN(ARG)*43758.5453D0
      U=H-DBLE(FLOOR(H))
      U=MIN(MAX(U,1.0D-4),1.0D0-1.0D-4)
      RETURN
      END
C=======================================================================
      SUBROUTINE KDAMAGE_TARGET(R,A,DMAX,D)
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
      SUBROUTINE KORTHO(E1,E2,E3,N12,N13,N23,G12,G13,G23,C)
      IMPLICIT NONE
      DOUBLE PRECISION E1,E2,E3,N12,N13,N23,G12,G13,G23
      DOUBLE PRECISION C(6,6),S11,S22,S33,S12,S13,S23,DET
      INTEGER I,J
      DO I=1,6
         DO J=1,6
            C(I,J)=0.0D0
         END DO
      END DO
      S11=1.0D0/E1
      S22=1.0D0/E2
      S33=1.0D0/E3
      S12=-N12/E1
      S13=-N13/E1
      S23=-N23/E2
      DET=S11*S22*S33+2.0D0*S12*S13*S23-
     1    S11*S23*S23-S22*S13*S13-S33*S12*S12
      IF (DET.LE.1.0D-30) THEN
         WRITE(7,*) 'Invalid orthotropic elastic constants; det=',DET
         CALL XIT
      END IF
      C(1,1)=(S22*S33-S23*S23)/DET
      C(2,2)=(S11*S33-S13*S13)/DET
      C(3,3)=(S11*S22-S12*S12)/DET
      C(1,2)=(S13*S23-S12*S33)/DET
      C(2,1)=C(1,2)
      C(1,3)=(S12*S23-S13*S22)/DET
      C(3,1)=C(1,3)
      C(2,3)=(S12*S13-S11*S23)/DET
      C(3,2)=C(2,3)
      C(4,4)=G12
      C(5,5)=G13
      C(6,6)=G23
      RETURN
      END
C=======================================================================
      SUBROUTINE KISO(E,NU,C)
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
      SUBROUTINE KMATVEC6(A,X,Y)
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
      SUBROUTINE KMISES(S,Q)
      IMPLICIT NONE
      DOUBLE PRECISION S(6),Q
      Q=SQRT(MAX(0.0D0,0.5D0*((S(1)-S(2))**2+
     1 (S(2)-S(3))**2+(S(3)-S(1))**2)+
     2 3.0D0*(S(4)**2+S(5)**2+S(6)**2)))
      RETURN
      END
C=======================================================================
      SUBROUTINE KPRINC(S,EV)
C     Jacobi eigenvalues for a real symmetric 3x3 stress tensor.
      IMPLICIT NONE
      DOUBLE PRECISION S(6),EV(3),A(3,3),APQ,APP,AQQ,TAU,T,C,SN
      DOUBLE PRECISION AKP,AKQ,AMAX,TOL,TMP
      INTEGER I,K,P,Q,ITER
      A(1,1)=S(1)
      A(2,2)=S(2)
      A(3,3)=S(3)
      A(1,2)=S(4)
      A(2,1)=S(4)
      A(1,3)=S(5)
      A(3,1)=S(5)
      A(2,3)=S(6)
      A(3,2)=S(6)
      TOL=1.0D-12*MAX(1.0D0,ABS(S(1))+ABS(S(2))+ABS(S(3))+
     1 ABS(S(4))+ABS(S(5))+ABS(S(6)))
      DO ITER=1,30
         P=1
         Q=2
         AMAX=ABS(A(1,2))
         IF (ABS(A(1,3)).GT.AMAX) THEN
            P=1
            Q=3
            AMAX=ABS(A(1,3))
         END IF
         IF (ABS(A(2,3)).GT.AMAX) THEN
            P=2
            Q=3
            AMAX=ABS(A(2,3))
         END IF
         IF (AMAX.LE.TOL) EXIT
         APQ=A(P,Q)
         APP=A(P,P)
         AQQ=A(Q,Q)
         TAU=(AQQ-APP)/(2.0D0*APQ)
         IF (TAU.GE.0.0D0) THEN
            T=1.0D0/(TAU+SQRT(1.0D0+TAU*TAU))
         ELSE
            T=-1.0D0/(-TAU+SQRT(1.0D0+TAU*TAU))
         END IF
         C=1.0D0/SQRT(1.0D0+T*T)
         SN=T*C
         A(P,P)=APP-T*APQ
         A(Q,Q)=AQQ+T*APQ
         A(P,Q)=0.0D0
         A(Q,P)=0.0D0
         DO K=1,3
            IF (K.NE.P .AND. K.NE.Q) THEN
               AKP=A(K,P)
               AKQ=A(K,Q)
               A(K,P)=C*AKP-SN*AKQ
               A(P,K)=A(K,P)
               A(K,Q)=SN*AKP+C*AKQ
               A(Q,K)=A(K,Q)
            END IF
         END DO
      END DO
      EV(1)=A(1,1)
      EV(2)=A(2,2)
      EV(3)=A(3,3)
C     Ascending sort.
      DO I=1,2
         DO K=I+1,3
            IF (EV(K).LT.EV(I)) THEN
               TMP=EV(I)
               EV(I)=EV(K)
               EV(K)=TMP
            END IF
         END DO
      END DO
      RETURN
      END
