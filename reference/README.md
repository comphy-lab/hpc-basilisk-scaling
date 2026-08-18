# Official Basilisk scaling tables

Unmodified `out-LEVEL-NRANKS` files from the Basilisk test tree, as
published on basilisk.fr:

- `curie/` — `src/test/mpi-circle/curie/` (CEA Curie). Cell counts are
  exactly \(2^{2L}\): these are full 2D grids, not the adaptive
  `mpi-circle.c` mesh.
- `occigen-3D/` — `src/test/mpi-laplacian/occigen/3D/` (CINES Occigen, 3D octree)

Source: local Basilisk darcs tree matching
https://basilisk.fr/src/test/mpi-circle.c and
https://basilisk.fr/src/test/mpi-laplacian.c.

These files are reference data, not MN5 results.
