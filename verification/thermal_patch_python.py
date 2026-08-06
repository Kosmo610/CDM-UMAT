"""
FREE thermal expansion patch test on the real RVE + real *Equation set.

One isotropic material, ONE coefficient of thermal expansion, drivers left
FREE (no prescribed macro strain, no macro stress).  Exact answer:

    sigma = 0  EVERYWHERE      and      eps = alpha * dT  (isotropic)

A single-phase body under uniform temperature change has nothing to fight,
so any non-zero stress is manufactured by the boundary conditions.  That is
exactly the failure mode that matters for this study: the cooling step is
where thermal residual stress is supposed to come from, and a constraint
defect would masquerade as physics.

Run:  python3 thermal_patch.py mesh.inp [twophase]
"""
import sys, json
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

src = open("pbc_patch.py", encoding="utf-8").read()
ns = {}
exec(src[:src.index("\nnodes, elems, nsets")], ns)

INP = sys.argv[1] if len(sys.argv) > 1 else "mesh.inp"
MODE = sys.argv[2] if len(sys.argv) > 2 else "single"     # single | twophase
DT = -1027.0                                              # 1050 C -> 23 C

# paper Table 1/2 + Chamis/Schapery yarn (transverse values used isotropically
# only to show the two-phase contrast; the single-phase run is the actual test)
E_M, NU_M, A_M = 350000.0, 0.2, 4.5e-6                    # SiC matrix
E_Y, NU_Y, A_Y = 44000.0, 0.25, 3.1e-6                    # yarn transverse-ish

nodes, elems, nsets, elsets, equations, bcs = ns["parse"](INP)
nid = sorted(nodes); idx = {n: i for i, n in enumerate(nid)}
X = np.array([nodes[n] for n in nid])
conn_i = np.vectorize(idx.get)(np.array([e[1:5] for e in elems]))
eid = np.array([e[0] for e in elems]); epos = {e: i for i, e in enumerate(eid)}
NE, NDOF = len(conn_i), 3 * len(nid)
drivers = [nsets[f"ConstraintsDriver{i}"][0] for i in range(6)]
real = np.array([i for n, i in idx.items() if n not in drivers])
L = X[real].max(0) - X[real].min(0)

is_yarn = np.zeros(NE, bool)
for y in range(4):
    for e in elsets[f"Yarn{y}"]:
        is_yarn[epos[e]] = True


def iso_C(E, nu):
    lam = E * nu / ((1 + nu) * (1 - 2 * nu)); mu = E / (2 * (1 + nu))
    C = np.zeros((6, 6)); C[:3, :3] = lam
    C[0, 0] = C[1, 1] = C[2, 2] = lam + 2 * mu
    C[3, 3] = C[4, 4] = C[5, 5] = mu
    return C


Cm, Cy = iso_C(E_M, NU_M), iso_C(E_Y, NU_Y)
Ce = np.where(is_yarn[:, None, None] & (MODE == "twophase"), Cy, Cm)
alpha = np.where(is_yarn & (MODE == "twophase"), A_Y, A_M)

P = X[conn_i]
J = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=1)
vol = np.linalg.det(J) / 6.0
if (vol < 0).any():
    bad = vol < 0
    conn_i[bad] = conn_i[bad][:, [0, 1, 3, 2]]
    P = X[conn_i]
    J = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=1)
    vol = np.linalg.det(J) / 6.0

Jinv = np.linalg.inv(J)
g = np.zeros((NE, 4, 3)); g[:, 1:, :] = np.transpose(Jinv, (0, 2, 1))
g[:, 0, :] = -g[:, 1:, :].sum(1)
B = np.zeros((NE, 6, 12))
for a in range(4):
    B[:, 0, 3 * a + 0] = g[:, a, 0]; B[:, 1, 3 * a + 1] = g[:, a, 1]
    B[:, 2, 3 * a + 2] = g[:, a, 2]
    B[:, 3, 3 * a + 0] = g[:, a, 1]; B[:, 3, 3 * a + 1] = g[:, a, 0]
    B[:, 4, 3 * a + 0] = g[:, a, 2]; B[:, 4, 3 * a + 2] = g[:, a, 0]
    B[:, 5, 3 * a + 1] = g[:, a, 2]; B[:, 5, 3 * a + 2] = g[:, a, 1]

ke = np.einsum("eki,ekl,elj,e->eij", B, Ce, B, vol)
edof = (conn_i[:, :, None] * 3 + np.arange(3)[None, None, :]).reshape(NE, 12)
K = sp.coo_matrix((ke.ravel(),
                   (np.repeat(edof, 12, axis=1).ravel(), np.tile(edof, (1, 12)).ravel())),
                  shape=(NDOF, NDOF)).tocsr()

# thermal load  f = int B^T C eps_th dV
eps_th = np.zeros((NE, 6)); eps_th[:, :3] = (alpha * DT)[:, None]
fe = np.einsum("eki,ekl,el,e->ei", B, Ce, eps_th, vol)
F = np.zeros(NDOF)
np.add.at(F, edof.ravel(), fe.ravel())

# ---- constraints: *Equation eliminated, corner fixed, DRIVERS LEFT FREE
eq_rows = []
for terms in equations:
    n = max(len(nsets[t[0]]) for t in terms)
    for k in range(n):
        eq_rows.append([(3 * idx[nsets[s][k] if len(nsets[s]) > 1 else nsets[s][0]] + d - 1, c)
                        for s, d, c in terms])
slave = {}
for ex in eq_rows:
    sd, sc = ex[0]
    assert sd not in slave
    slave[sd] = [(d, -c / sc) for d, c in ex[1:]]

presc = {}
for setname, d1, d2 in bcs:
    for node in nsets[setname]:
        for d in range(d1, d2 + 1):
            presc[3 * idx[node] + d - 1] = 0.0
for dn in drivers:                       # only dof 1 carries strain; 2,3 are dummies
    presc[3 * idx[dn] + 1] = 0.0
    presc[3 * idx[dn] + 2] = 0.0
print(f"slaves {len(slave)}   prescribed {len(presc)}   (drivers dof1 FREE)")

free = np.array(sorted(set(range(NDOF)) - set(slave) - set(presc)))
fpos = {d: i for i, d in enumerate(free)}
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
            g0[s] += coef * g0[d]
T = sp.coo_matrix((v, (r, c)), shape=(NDOF, len(free))).tocsr()

Kr = (T.T @ K @ T).tocsc()
fr = T.T @ (F - K @ g0)
u = T @ spla.spsolve(Kr, fr) + g0

eps_e = np.einsum("ekj,ej->ek", B, u[edof])
sig_e = np.einsum("ekl,el->ek", Ce, eps_e - eps_th)
mac = np.array([u[3 * idx[drivers[i]]] for i in range(6)])

exact = A_M * DT
scale = np.abs(Ce[:, 0, 0] * eps_th[:, 0]).max()      # stress the material could carry
rep = {
    "mode": MODE, "dT": DT,
    "macro_strain_drivers": mac.tolist(),
    "exact_free_strain": exact,
    "max_abs_stress_MPa": float(np.abs(sig_e).max()),
    "stress_over_blocked_scale": float(np.abs(sig_e).max() / scale),
    "vol_avg_stress_MPa": ((sig_e * vol[:, None]).sum(0) / vol.sum()).tolist(),
}
if MODE == "single":
    rep["driver_strain_err"] = float(max(abs(mac[i] - exact) for i in range(3)))
    rep["shear_driver_max"] = float(np.abs(mac[3:]).max())
print(json.dumps(rep, indent=2))
json.dump(rep, open(f"thermal_{MODE}.json", "w"), indent=2)
