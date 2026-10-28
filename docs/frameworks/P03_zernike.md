# P03, Zernike aberrations (Noll order)

Physics component. Wavefront aberrations of the optical system are written as a sum of Zernike modes in Noll order,
orthonormal over the unit disc. The same basis injects an aberration into the simulation, corrects it (M14) and states the
distribution that the robust hologram (B4) is optimised for.

| Item | Value |
|---|---|
| Module | `data-pipeline/pipeline/model/holo/core/zernike.py` |
| Tests | `tests/engine/test_zernike.py` |
| Used by | M14, B4, case C09 |

## Purpose

An aberrated wavefront $W(\rho,\theta)$ adds a phase $2\pi W$ to the SLM phase (the aberration phase is always added to the
final SLM phase, as in the total-phase sum of Nogrette et al. 2014, https://arxiv.org/abs/1402.5329 ). Expanding $W$ in a
standard basis gives each aberration a name, an amplitude in waves and a place in a ranked list.

## Equations

$$Z_n^m(\rho,\theta) = N_n^m\, R_n^{|m|}(\rho)\begin{cases}\cos(m\theta) & m \ge 0\\ \sin(|m|\theta) & m < 0\end{cases}, \qquad
R_n^{|m|}(\rho) = \sum_{s=0}^{(n-|m|)/2} \frac{(-1)^s\,(n-s)!}{s!\,\big(\frac{n+|m|}{2}-s\big)!\,\big(\frac{n-|m|}{2}-s\big)!}\,\rho^{\,n-2s}$$

with the normalisation $N_n^m = \sqrt{2(n+1)}$ for $m \ne 0$ and $\sqrt{n+1}$ for $m = 0$, which gives unit rms over the disc
(`zernike.py`, `zernike`, line 72). With this basis the rms wavefront error is the root sum of squares of the coefficients,
$\sigma_W$ in waves, excluding piston (`rms_waves`, line 112). The Maréchal approximation gives the Strehl ratio

$$S \approx \exp\!\big[-(2\pi\sigma_W)^2\big], \qquad S > 0.8 \text{ for } \sigma_W < 1/14 \text{ wave}$$

(`strehl`, line 120). The definitions, the orthogonality $\int Z Z'\,\rho\,d\rho\,d\theta = \pi\epsilon_m \delta\delta'$ and the
Noll table for $j = 1$ to 11 were read from the Janssen documentation page and a secondary table; they were not read in
Noll's paper.

Noll indices $j$ map to $(n, m)$ through `noll_to_nm` (line 41): $j = 1$ to 11 are piston, tip, tilt, defocus, oblique and
vertical astigmatism, vertical and horizontal coma, vertical and oblique trefoil, primary spherical; $j = 12$ to 15 are
$(4,2), (4,-2), (4,4), (4,-4)$ from a secondary table; for $j = 12$ to 21 the module applies the Noll rule: within an $n$, even
$j$ takes the cosine term, odd $j$ the sine term, ordered by increasing $|m|$. The pupil radius is half the SLM side; pixels
outside the disc (the corners) are zero (`wavefront_waves`, line 91; `phase_from_coeffs`, line 107).

## Implementation

- Entrypoints: `zernike.noll_to_nm`, `zernike_name`, `zernike`, `wavefront_waves`, `phase_from_coeffs`, `rms_waves`, `strehl`.
- Limit: `J_MAX = 21` coefficients (Noll $j = 1$ to 21); `phase_from_coeffs` returns the wavefront wrapped to $[0, 2\pi)$.

## Acceptance criterion and test

The 21 modes are orthonormal over the disc (Gram matrix within 1e-3, `tests/engine/test_zernike.py::test_orthonormal_over_disc`);
the Noll table equals the research table (`::test_noll_table_matches_dossier`); the rms equals the root sum of squares and
matches samples (`::test_rms_equals_root_sum_of_squares_and_matches_samples`); the Maréchal relation holds (`::test_strehl_marechal`).

## Measured values (DinHot measurement, engine test run of 2026-10-28)

Gram matrix of the 21 modes sampled on the disc: deviation from the identity within 1e-3 (the test bound).

## Limits

- UNVERIFIED: Noll 1976 (https://doi.org/10.1364/JOSA.66.000207 ) is paywalled and was not opened. The index table and the
  normalisation come from secondary sources (the Janssen page, a University of Arizona page, Wikipedia); $j = 12$ to 21 follow
  the Noll rule, and $j = 21$ is derived. Sign conventions differ between sources.
- The Maréchal relation is an approximation valid for small $\sigma_W$.

## References

- Noll 1976, J. Opt. Soc. Am. 66, 207, https://doi.org/10.1364/JOSA.66.000207 (abstract only)
- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Zernike polynomials, https://en.wikipedia.org/wiki/Zernike_polynomials (secondary, index table)
