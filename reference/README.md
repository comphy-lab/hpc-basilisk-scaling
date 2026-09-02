# Published Basilisk scaling tables

Unmodified `out-LEVEL-NRANKS` files from the Basilisk test tree, as
published on basilisk.fr:

- `curie/` is `src/test/mpi-circle/curie/` (CEA Curie). The cell counts are
  exactly $2^{2L}$, so these are full 2D grids rather than the adaptive
  `mpi-circle.c` mesh. Overlay them only against a uniform run at the same
  level.
- `occigen-3D/` is `src/test/mpi-laplacian/occigen/3D/` (CINES Occigen, 3D
  octree).

Both sets come from a local Basilisk darcs tree matching
https://basilisk.fr/src/test/mpi-circle.c and
https://basilisk.fr/src/test/mpi-laplacian.c.

`marangoni.ref` is the basilisk.fr Al Saud terminal-velocity table: points
per $R$, computed $u/U_{\mathrm{drop}}$ and theory. It is the reference the
validation figure compares against, not a live run.

Nothing in this directory was produced by the campaigns in this repository.
