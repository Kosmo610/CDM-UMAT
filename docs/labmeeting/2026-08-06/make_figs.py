"""Figures for the lab-meeting deck, built from the real mesh + real patch-test solve."""
import numpy as np, json, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

EMBER, STEEL, GREEN, INK, MUTED = "#D9542B", "#3F6B7D", "#2F6B4F", "#1A1D21", "#6E7681"
YARNC = ["#D9542B", "#E08A5F", "#3F6B7D", "#6E9AAC"]
MATC = "#DDE1E6"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#9AA1A9",
                     "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 9})

# ------------------------------------------------------------------ load
src = open("pbc_patch.py", encoding="utf-8").read()
ns = {}; exec(src[:src.index("\nnodes, elems, nsets")], ns)
nodes, elems, nsets, elsets, equations, bcs = ns["parse"]("mesh.inp")
nid = sorted(nodes); idx = {n: i for i, n in enumerate(nid)}
X = np.array([nodes[n] for n in nid])
conn = np.array([e[1:5] for e in elems]); eid = np.array([e[0] for e in elems])
epos = {e: i for i, e in enumerate(eid)}
conn_i = np.vectorize(idx.get)(conn)
L = np.array([3.5, 3.5, 0.44])

phase = np.full(len(conn), -1)                       # 0..3 yarn, -1 matrix
for y in range(4):
    for e in elsets[f"Yarn{y}"]:
        phase[epos[e]] = y

D = {c: np.load(f"patch_{c}.npz") for c in ("exx", "exy")}
R = {c: json.load(open(f"patch_{c}.json")) for c in ("exx", "exy")}


def boundary_tris(mask):
    """outward triangles of the sub-mesh selected by `mask` (element bool array)"""
    F = [[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]]
    cnt = collections.Counter()
    keep = {}
    for c in conn_i[mask]:
        for f in F:
            t = (c[f[0]], c[f[1]], c[f[2]])
            k = tuple(sorted(t))
            cnt[k] += 1
            keep[k] = t
    return np.array([keep[k] for k, v in cnt.items() if v == 1])


# =========================================================== FIG 1 : RVE
fig = plt.figure(figsize=(9.6, 4.3))
ax = fig.add_subplot(121, projection="3d")
for y in range(4):
    tri = boundary_tris(phase == y)
    ax.add_collection3d(Poly3DCollection(X[tri], facecolor=YARNC[y], edgecolor="none",
                                         alpha=0.95, linewidth=0))
ax.set_xlim(0, 3.5); ax.set_ylim(0, 3.5); ax.set_zlim(-1.5, 1.96)
ax.set_box_aspect((3.5, 3.5, 3.46))
ax.view_init(elev=26, azim=-58)
ax.set_axis_off()
ax.text2D(0.02, 0.94, "yarns only  (2 warp $\\parallel x$ + 2 weft $\\parallel y$)",
          transform=ax.transAxes, fontsize=9.5, color=INK, weight="bold")
ax.text2D(0.02, 0.02, "matrix hidden", transform=ax.transAxes, fontsize=8.5, color=MUTED)

ax2 = fig.add_subplot(122, projection="3d")
tri = boundary_tris(np.ones(len(conn), bool))
ax2.add_collection3d(Poly3DCollection(X[tri], facecolor=MATC, edgecolor="#B9C0C8",
                                      alpha=0.55, linewidth=0.12))
ax2.set_xlim(0, 3.5); ax2.set_ylim(0, 3.5); ax2.set_zlim(-1.5, 1.96)
ax2.set_box_aspect((3.5, 3.5, 3.46))
ax2.view_init(elev=26, azim=-58)
ax2.set_axis_off()
ax2.text2D(0.02, 0.94, "full RVE  26,452 C3D4", transform=ax2.transAxes,
           fontsize=9.5, color=INK, weight="bold")
ax2.text2D(0.02, 0.02, "3.5 $\\times$ 3.5 $\\times$ 0.44 mm    $V_f$ = 0.40",
           transform=ax2.transAxes, fontsize=8.5, color=MUTED)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0)
fig.savefig("fig_rve.png", dpi=200, facecolor="white")
plt.close(fig)
print("fig_rve.png")


# ================================================ FIG 2 : face pairing + check
real = np.array([i for n, i in idx.items() if not str(n).startswith("x")])
drv = [nsets[f"ConstraintsDriver{i}"][0] for i in range(6)]
real = np.array([i for n, i in idx.items() if n not in drv])
X0, X1 = X[real].min(0), X[real].max(0)

fA = np.array([idx[n] for n in nsets["FaceA"]])
fB = np.array([idx[n] for n in nsets["FaceB"]])
fE = np.array([idx[n] for n in nsets["FaceE"]])
fF = np.array([idx[n] for n in nsets["FaceF"]])
inplane = np.abs(X[fE][:, :2] - X[fF][:, :2]).max()

U = D["exx"]["U"]
duA = U[fA] - U[fB]
exact = 1e-3 * L[0]
err = duA[:, 0] - exact
m = np.abs(err).max()

fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.3),
                        gridspec_kw={"width_ratios": [1.0, 1.25]})
ax = axs[0]
ax.scatter(X[fF, 0], X[fF, 1], s=42, facecolor="none", edgecolor=STEEL, lw=1.0,
           label=f"FaceF   z = 0        ({len(fF)} nodes)", zorder=2)
ax.scatter(X[fE, 0], X[fE, 1], s=7, color=EMBER,
           label=f"FaceE   z = $L_z$    ({len(fE)} nodes)", zorder=3)
ax.set_aspect("equal"); ax.set_xlabel("x  [mm]"); ax.set_ylabel("y  [mm]")
ax.set_title("opposite faces carry the identical node pattern",
             fontsize=10.5, color=INK, weight="bold")
ax.text(0.02, -0.30, f"max in-plane offset between the two patterns:  {inplane:.1e} mm",
        transform=ax.transAxes, fontsize=9.5, color=GREEN, weight="bold")
ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=1,
          bbox_to_anchor=(0.5, -0.12))

ax = axs[1]
ax.axhline(exact, color=EMBER, lw=1.4, zorder=1,
           label=f"target  $\\varepsilon_x L_x$ = {exact:.4f} mm")
ax.scatter(np.arange(len(fA)), duA[:, 0], s=26, color=GREEN, zorder=3,
           label="computed  $(u_A - u_B)_x$")
ax.set_xlabel("x-face node pair index  (FaceA $\\leftrightarrow$ FaceB, 58 pairs)")
ax.set_ylabel("$u_A - u_B$   [mm]")
ax.set_ylim(exact - 4e-4, exact + 4e-4)
ax.set_title("every pair sits exactly on the prescribed jump",
             fontsize=10.5, color=INK, weight="bold")
ax.text(0.03, 0.10, f"max deviation over all 58 pairs:  {m:.1e} mm",
        transform=ax.transAxes, fontsize=9.5, color=GREEN, weight="bold")
ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2,
          bbox_to_anchor=(0.5, -0.16))
for a in axs:
    a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
fig.tight_layout()
fig.savefig("fig_pair.png", dpi=200, facecolor="white", bbox_inches="tight")
plt.close(fig)
print(f"fig_pair.png   in-plane offset {inplane:.2e} mm   max pair deviation {m:.2e} mm")


# ============================================ FIG 3 : deformed cell tiles 3x3
yarn_tris, yarn_ph = [], []
for y in range(4):
    t = boundary_tris(phase == y)
    yarn_tris.append(t); yarn_ph.append(np.full(len(t), y))
yarn_tris = np.vstack(yarn_tris); yarn_ph = np.concatenate(yarn_ph)
print(f"yarn surface triangles: {len(yarn_tris)}")

S = 300.0
fig, axs = plt.subplots(1, 2, figsize=(12.4, 6.2))
for ax, case, tag in zip(axs, ("exx", "exy"),
                         ("tension   $\\varepsilon_x = 10^{-3}$",
                          "shear   $\\varepsilon_{xy} = 10^{-3}$")):
    U = D[case]["U"]
    H = np.zeros((3, 3))
    if case == "exx": H[0, 0] = 1e-3
    else:             H[0, 1] = 1e-3
    Xd = X + S * U
    Xd[:, :2] -= Xd[real][:, :2].min(0)                # real nodes only
    a1 = np.array([L[0], 0, 0]); a2 = np.array([0, L[1], 0])
    a1d = a1 + S * (H @ a1); a2d = a2 + S * (H @ a2)

    order = np.argsort(Xd[yarn_tris][:, :, 2].mean(1))
    tri_s = yarn_tris[order]; cols = np.array(YARNC)[yarn_ph[order]]

    for i in range(3):
        for j in range(3):
            off = i * a1d + j * a2d
            centre = (i == 1 and j == 1)
            V = Xd[:, :2] + off[:2]
            ax.add_collection(PolyCollection(
                V[tri_s], facecolors=cols, edgecolors="none",
                alpha=1.0 if centre else 0.28, zorder=3 if centre else 2))
            corner = np.array([[0, 0], a1d[:2], a1d[:2] + a2d[:2], a2d[:2], [0, 0]]) + off[:2]
            ax.plot(corner[:, 0], corner[:, 1], color=INK if centre else "#AEB5BD",
                    lw=2.0 if centre else 0.8, zorder=5)
    pts = np.array([i * a1d[:2] + j * a2d[:2] for i in range(4) for j in range(4)])
    ax.set_xlim(pts[:, 0].min() - 0.2, pts[:, 0].max() + 0.2)
    ax.set_ylim(pts[:, 1].min() - 0.2, pts[:, 1].max() + 0.2)
    ax.set_aspect("equal"); ax.set_axis_off()
    gap = np.abs(Xd[fA] - Xd[fB] - a1d).max()
    ax.set_title(tag, fontsize=11.5, color=INK, weight="bold", pad=8)
    ax.text(0.5, -0.015, f"seam mismatch at every tile boundary:  {gap:.1e} mm",
            transform=ax.transAxes, ha="center", fontsize=10, color=GREEN, weight="bold")
    print(f"  {case}: seam {gap:.3e} mm")
fig.suptitle("deformed unit cell tiled 3 $\\times$ 3   (displacement $\\times$300, yarns only)",
             fontsize=12.5, color=INK, weight="bold", y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig("fig_tile.png", dpi=190, facecolor="white")
plt.close(fig)
print("fig_tile.png")


# ==================================================== FIG 4 : patch test pass
fig, axs = plt.subplots(1, 2, figsize=(11.0, 3.6))
for ax, case, ttl, comp in zip(axs, ("exx", "exy"),
                               ("tension   $\\varepsilon_x = 10^{-3}$",
                                "shear   $\\varepsilon_{xy} = 10^{-3}$"),
                               ("$\\sigma_{xx}$", "$\\sigma_{xy}$")):
    sig = D[case]["sig"]
    k = 0 if case == "exx" else 3
    s_ = sig[:, k]
    dev = (s_ - s_.mean()) * 1e10                      # units of 1e-10 MPa
    ax.hist(dev, bins=70, color=STEEL, alpha=0.9)
    ax.axvline(0, color=EMBER, lw=1.4)
    ax.set_xlabel(f"{comp} $-$ mean     [$10^{{-10}}$ MPa]")
    ax.set_ylabel("elements")
    ax.set_title(ttl, fontsize=10.5, color=INK, weight="bold")
    ax.text(0.03, 0.93,
            f"mean = {s_.mean():.6f} MPa\nexact = {R[case]['sigma_exact'][k]:.6f} MPa\n"
            f"spread = {np.ptp(s_):.2e} MPa   (26,452 elements)",
            transform=ax.transAxes, fontsize=9, va="top", color=INK)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
fig.suptitle("patch test — one isotropic material, PBC driven: the stress field is uniform to $10^{-12}$",
             fontsize=11.5, color=INK, weight="bold", y=1.0)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("fig_patch.png", dpi=200, facecolor="white")
plt.close(fig)
print("fig_patch.png")

summary = {c: {k: R[c][k] for k in ("stress_uniformity_ptp_over_scale",
                                    "strain_uniformity_ptp_over_eps",
                                    "fluctuation_spread_over_HL",
                                    "C_col1_rel_err", "volume_fill_percent")} for c in R}
summary["face_pattern_offset_mm"] = float(inplane)
summary["pair_jump_max_dev_mm"] = float(m)
json.dump(summary, open("patch_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
