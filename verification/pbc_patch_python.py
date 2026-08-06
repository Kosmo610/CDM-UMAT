"""
Independent Python re-solve of the TexGen RVE patch test.

Reads the real deck (nodes, C3D4 elements, *NSet, *Boundary, *Equation),
fills the whole cell with ONE isotropic material, drives a macroscopic
strain through the ConstraintsDriver nodes, and checks the closed-form
answer:  uniform strain everywhere, zero periodic fluctuation, C = C_iso.

Nothing here shares code with Abaqus or with verification/check_pbc.py.
"""
import re, sys, json
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

INP  = sys.argv[1] if len(sys.argv) > 1 else "mesh.inp"
CASE = sys.argv[2] if len(sys.argv) > 2 else "exx"   # exx | exy
E_ISO, NU_ISO = 350000.0, 0.2          # MPa — SiC matrix (paper Table 2)
EPS = 1.0e-3                            # driven macroscopic strain


# ------------------------------------------------------------------ parse
def parse(path):
    nodes, elems, nsets, elsets, equations, bcs = {}, [], {}, {}, [], []
    mode, cur, pend = None, None, None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            head = line.split(",")[0].strip().lower()
            opts = {}
            for tok in line.split(",")[1:]:
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    opts[k.strip().lower()] = v.strip()
                else:
                    opts[tok.strip().lower()] = True
            if head == "*node":
                mode = "node"
            elif head == "*element":
                mode = "elem"
            elif head == "*nset":
                mode = "nset"
                cur = opts.get("nset")
                nsets.setdefault(cur, [])
                if opts.get("generate"):
                    mode = "nset_gen"
            elif head == "*elset":
                mode = "elset"
                cur = opts.get("elset")
                elsets.setdefault(cur, [])
                if opts.get("generate"):
                    mode = "elset_gen"
            elif head == "*equation":
                mode, pend = "eq_n", None
            elif head == "*boundary":
                mode = "bc"
            else:
                mode = None
            continue

        if mode == "node":
            p = [x.strip() for x in line.split(",")]
            nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == "elem":
            p = [int(x) for x in line.split(",")]
            elems.append(p)                      # [eid, n1..n4]
        elif mode in ("nset", "elset"):
            tgt = nsets[cur] if mode == "nset" else elsets[cur]
            tgt.extend(int(x) for x in line.split(",") if x.strip())
        elif mode in ("nset_gen", "elset_gen"):
            a, b, c = [int(x) for x in line.split(",")[:3]]
            tgt = nsets[cur] if mode == "nset_gen" else elsets[cur]
            tgt.extend(range(a, b + 1, c))
        elif mode == "eq_n":
            pend = [int(line.split(",")[0]), []]      # [declared term count, tokens]
            mode = "eq_terms"
        elif mode == "eq_terms":
            # an *Equation card may run over several lines; keep reading until the
            # declared number of (set, dof, coeff) triples has been collected
            pend[1].extend(x.strip() for x in line.split(",") if x.strip())
            if len(pend[1]) >= 3 * pend[0]:
                p = pend[1]
                terms = [(p[i], int(p[i + 1]), float(p[i + 2]))
                         for i in range(0, 3 * pend[0], 3)]
                equations.append(terms)
                mode, pend = None, None
        elif mode == "bc":
            p = [x.strip() for x in line.split(",")]
            bcs.append((p[0], int(p[1]), int(p[2]) if len(p) > 2 else int(p[1])))
    return nodes, elems, nsets, elsets, equations, bcs


nodes, elems, nsets, elsets, equations, bcs = parse(INP)
nid = sorted(nodes)
idx = {n: i for i, n in enumerate(nid)}
X = np.array([nodes[n] for n in nid])
conn = np.array([e[1:5] for e in elems])
conn_i = np.vectorize(idx.get)(conn)
NN, NE, NDOF = len(nid), len(conn), 3 * len(nid)

drivers = [nsets[f"ConstraintsDriver{i}"][0] for i in range(6)]
real = np.array([i for n, i in idx.items() if n not in drivers])
L = X[real].max(0) - X[real].min(0)
print(f"nodes {NN} (real {len(real)} + 6 driver)   elements {NE}   box {L}")


# ------------------------------------------------- C3D4 stiffness assembly
def iso_C(E, nu):
    lam = E * nu / ((1 + nu) * (1 - 2 * nu))
    mu = E / (2 * (1 + nu))
    C = np.zeros((6, 6))
    C[:3, :3] = lam
    C[0, 0] = C[1, 1] = C[2, 2] = lam + 2 * mu
    C[3, 3] = C[4, 4] = C[5, 5] = mu
    return C


C6 = iso_C(E_ISO, NU_ISO)
P = X[conn_i]                                        # (NE,4,3)
J = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=1)
detJ = np.linalg.det(J)
vol = detJ / 6.0
if (vol <= 0).any():                                 # fix inverted tets
    bad = vol < 0
    conn_i[bad] = conn_i[bad][:, [0, 1, 3, 2]]
    P = X[conn_i]
    J = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=1)
    vol = np.linalg.det(J) / 6.0
print(f"volume  sum {vol.sum():.6f} mm^3   box {np.prod(L):.6f}   fill {vol.sum()/np.prod(L)*100:.4f} %")

Jinv = np.linalg.inv(J)                              # (NE,3,3)
g = np.zeros((NE, 4, 3))
g[:, 1:, :] = np.transpose(Jinv, (0, 2, 1))
g[:, 0, :] = -g[:, 1:, :].sum(1)                     # dN/dx  (NE,4,3)

B = np.zeros((NE, 6, 12))
for a in range(4):
    B[:, 0, 3 * a + 0] = g[:, a, 0]
    B[:, 1, 3 * a + 1] = g[:, a, 1]
    B[:, 2, 3 * a + 2] = g[:, a, 2]
    B[:, 3, 3 * a + 0] = g[:, a, 1]; B[:, 3, 3 * a + 1] = g[:, a, 0]
    B[:, 4, 3 * a + 0] = g[:, a, 2]; B[:, 4, 3 * a + 2] = g[:, a, 0]
    B[:, 5, 3 * a + 1] = g[:, a, 2]; B[:, 5, 3 * a + 2] = g[:, a, 1]

ke = np.einsum("eki,kl,elj,e->eij", B, C6, B, vol)
edof = (conn_i[:, :, None] * 3 + np.arange(3)[None, None, :]).reshape(NE, 12)
rows = np.repeat(edof, 12, axis=1).ravel()
cols = np.tile(edof, (1, 12)).ravel()
K = sp.coo_matrix((ke.ravel(), (rows, cols)), shape=(NDOF, NDOF)).tocsr()
print(f"K assembled  {K.shape}  nnz {K.nnz}")


# --------------------------------------------------- expand *Equation cards
def members(name):
    return nsets[name]


eq_rows = []                                          # (slave_dof, [(dof,coef)...])
for terms in equations:
    lens = {len(members(t[0])) for t in terms}
    n = max(lens)
    for k in range(n):
        expanded = []
        for setname, dof, coef in terms:
            m = members(setname)
            node = m[k] if len(m) > 1 else m[0]
            expanded.append((3 * idx[node] + dof - 1, coef))
        eq_rows.append(expanded)
print(f"equation cards {len(equations)}  ->  {len(eq_rows)} scalar equations")

slave = {}
for ex in eq_rows:
    s_dof, s_c = ex[0]
    assert s_dof not in slave, f"DOF {s_dof} eliminated twice (overconstraint)"
    slave[s_dof] = [(d, -c / s_c) for d, c in ex[1:]]

# prescribed: *Boundary + all six driver nodes (every driver DOF is driven)
presc = {}
for setname, d1, d2 in bcs:
    for node in members(setname):
        for d in range(d1, d2 + 1):
            presc[3 * idx[node] + d - 1] = 0.0
for k, dn in enumerate(drivers):
    for d in range(3):
        presc[3 * idx[dn] + d] = 0.0
DRV = {"exx": 0, "exy": 3}[CASE]                      # 0=e_x .. 3=e_xy
presc[3 * idx[drivers[DRV]] + 0] = EPS                # one component on, rest clamped to 0
print(f"slaves {len(slave)}   prescribed {len(presc)}")

assert not (set(slave) & set(presc)), "a DOF is both eliminated and prescribed"
free = np.array(sorted(set(range(NDOF)) - set(slave) - set(presc)))
fpos = {d: i for i, d in enumerate(free)}

# u = T u_free + g0
r, c, v, g0 = [], [], [], np.zeros(NDOF)
for d in free:
    r.append(d); c.append(fpos[d]); v.append(1.0)
for d, val in presc.items():
    g0[d] = val
for s, deps in slave.items():
    for d, coef in deps:
        if d in fpos:
            r.append(s); c.append(fpos[d]); v.append(coef)
        else:
            g0[s] += coef * g0[d]                     # depends on a prescribed DOF
T = sp.coo_matrix((v, (r, c)), shape=(NDOF, len(free))).tocsr()

Kr = (T.T @ K @ T).tocsc()
fr = -(T.T @ (K @ g0))
print(f"reduced system {Kr.shape}  nnz {Kr.nnz}   solving ...")
u_free = spla.spsolve(Kr, fr)
u = T @ u_free + g0
print("solved.")


# ------------------------------------------------------------- patch checks
U = u.reshape(-1, 3)
eps_e = np.einsum("ekj,ej->ek", B, u[edof])           # (NE,6) element strains
sig_e = eps_e @ C6.T

H = np.zeros((3, 3))                                  # macroscopic gradient
if CASE == "exx":
    H[0, 0] = EPS
else:
    H[0, 1] = EPS                                     # TexGen e_xy sits in H[0,1]
fluct = U - X @ H.T
fl_real = fluct[real]

sig_mean = np.abs(sig_e).mean(0)
report = {
    "case": CASE,
    "driven_strain": EPS,
    "strain_mean": float(eps_e[:, 0].mean() if CASE == "exx" else eps_e[:, 3].mean()),
    "stress_uniformity_ptp_over_scale": float(
        max(np.ptp(sig_e[:, k]) for k in range(6)) / np.abs(sig_e).max()),
    "strain_uniformity_ptp_over_eps": float(
        max(np.ptp(eps_e[:, k]) for k in range(6)) / EPS),
    "fluctuation_spread_over_HL": float(
        (fl_real.max(0) - fl_real.min(0)).max() / (EPS * L[0])),
    "volume_fill_percent": float(vol.sum() / np.prod(L) * 100.0),
}

# homogenised C column 1 from the volume average  (sigma = <sigma>)
sig_avg = (sig_e * vol[:, None]).sum(0) / vol.sum()
C_exact = C6[:, 0 if CASE == "exx" else 3] * EPS
report["C_col1_rel_err"] = float(np.abs(sig_avg - C_exact).max() / np.abs(C_exact).max())
report["sigma_avg"] = sig_avg.tolist()
report["sigma_exact"] = C_exact.tolist()

print(json.dumps(report, indent=2))
np.savez_compressed(f"patch_{CASE}.npz", X=X, conn=conn_i, U=U, sig=sig_e, eps=eps_e,
                    vol=vol, L=L, real=real,
                    faceA=[idx[n] for n in nsets["FaceA"]],
                    faceB=[idx[n] for n in nsets["FaceB"]],
                    faceC=[idx[n] for n in nsets["FaceC"]],
                    faceD=[idx[n] for n in nsets["FaceD"]])
json.dump(report, open(f"patch_{CASE}.json", "w"), indent=2)
print(f"wrote patch_{CASE}.npz / patch_{CASE}.json")
