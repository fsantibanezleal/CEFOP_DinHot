# P04, Trap physics (bead stiffness and atom dipole trap)

Physics component. The computed focal intensity is converted into what a trapped particle feels: the stiffness of a small
dielectric bead in the Rayleigh regime, and the depth and oscillation frequencies of a neutral-atom dipole trap.

| Item | Value |
|---|---|
| Module | `data-pipeline/pipeline/model/holo/core/trapphys.py` |
| Tests | `tests/engine/test_trapphys.py` |
| Used by | the Dynamics views, the C01 and C03 particle drivers, the depth view |

## Purpose

The hologram metrics say how equal the traps are; trap physics says what that means in newtons per metre or in kilohertz.
Units are carried in the names (`_m`, `_N_per_m`, `_W_per_m2`, `_J`, `_rad_s`, `_Fm2`).

## Equations

### Rayleigh bead

The polarizability of a sphere of radius $r$ with $\epsilon_r = (n_{particle}/n_{medium})^2$ is

$$\alpha_0 = 4\pi r^3 \epsilon_0\,\frac{\epsilon_r - 1}{\epsilon_r + 2}$$

(Eq. 5, Clausius-Mossotti; `rayleigh_polarizability_Fm2`, line 41). The time-averaged gradient force is
$F = \tfrac12 \operatorname{Re}(\alpha)/(c\epsilon_0)\,\nabla I$ (Eq. 9). For a Gaussian focus $I = I_0 \exp(-2\rho^2/w_0^2)$
the stiffness is

$$\kappa = \frac{2\operatorname{Re}(\alpha)\, I_0}{c\,\epsilon_0\, w_0^2}, \qquad U = \tfrac12 \kappa\rho^2$$

(Eqs. 12 to 14; `gaussian_stiffness_N_per_m`, line 58). In general
$\kappa_i = -\operatorname{Re}(\alpha)/(2 c\epsilon_0)\; \partial^2 I/\partial x_i^2$, evaluated on a focal intensity map by `stiffness_map`
(line 64) with 3-point central differences. Source: Bouloumis and Nic Chormaic, arXiv 2001.07359, Eqs. 5 to 14, who follow Harada
and Asakura 1996 (not opened). The vacuum prefactor is kept: the extra medium factors of a bead in water are not in the
section read (UNVERIFIED), so the magnitude carries that caveat. Radiation reaction and the scattering force are not modelled.

### Atom in a dipole trap

$$U_{dip} = \frac{3\pi c^2}{2\omega_0^3}\,\frac{\Gamma}{\Delta}\,I, \qquad
\Gamma_{sc} = \frac{3\pi c^2}{2\hbar\omega_0^3}\Big(\frac{\Gamma}{\Delta}\Big)^2 I, \qquad \hbar\Gamma_{sc} = \frac{\Gamma}{\Delta}\,U_{dip}$$

with $\Delta = \omega - \omega_0$; red detuning ($\Delta < 0$) is attractive (Eqs. 12 to 14; `dipole_potential_J`, line 91;
`scattering_rate_per_s`, line 99). A focused Gaussian beam gives $I(r,z) = \frac{2P}{\pi w^2(z)}\exp(-2r^2/w^2(z))$ (Eq. 36),
$z_R = \pi w_0^2/\lambda$ (Eq. 37) and $U = -\hat U\,[1 - 2(r/w_0)^2 - (z/z_R)^2]$ (Eq. 38), hence

$$\omega_r = \sqrt{\frac{4\hat U}{m w_0^2}}, \qquad \omega_z = \sqrt{\frac{2\hat U}{m z_R^2}}$$

(`dipole_trap_depth_J`, line 107; `trap_frequencies_rad_s`). Source: Grimm, Weidemuller and Ovchinnikov 2000,
https://arxiv.org/abs/physics/9902072 . Constants: SI 2019 exact values of $c$, $k_B$, $h$ and the CODATA 2018 value of
$\epsilon_0$.

## Implementation

- Entrypoints: `trapphys.rayleigh_polarizability_Fm2`, `gaussian_stiffness_N_per_m`, `stiffness_map`, `dipole_potential_J`,
  `dipole_trap_depth_J`, `trap_frequencies_rad_s`, `rayleigh_range_m`. A blue-detuned request raises `ValueError` (no trap).
- Case use: C03 puts a rubidium atom (87 amu) in trap 528 at 3 W with a detuning of -31.5 THz; C01 puts a 0.5 um bead
  (particle index 1.59, viscosity 0.00089 Pa s, 295 K) in trap 4 at 10 mW
  (`data-pipeline/pipeline/cases/library.py`, lines 130 to 132 and 172 to 173).

## Acceptance criterion and test

The stiffness map of a Gaussian focus matches the analytic stiffness (`tests/engine/test_trapphys.py::test_stiffness_map_matches_analytic_gaussian`);
the polarizability follows Clausius-Mossotti and the $r^3$ scaling (`::test_polarizability_clausius_mossotti_and_r3_scaling`);
the trap depth and frequencies reproduce a derived atom check (`::test_trap_depth_and_frequencies_ebadi_check`).

## Measured values (DinHot measurement, engine test run of 2026-10-28)

The Ebadi check: a radial frequency of 99 kHz within 2 percent of the value derived from Ebadi et al. 2021
(https://arxiv.org/abs/2012.12281 ), a check derived in DinHot's research record, not a quoted result. In the C03 bake driver an
atom oscillates at 102.4 kHz against 105.1 kHz expected, with a depth of 892 uK (measured with planted test methods during the
producer's development; the canonical bake restates it).

## Limits

- Rayleigh regime only (bead radius small against the wavelength); the vacuum prefactor caveat above.
- The atom is a two-level dipole trap; multilevel light shifts are not modelled.

## References

- Bouloumis and Nic Chormaic, arXiv 2001.07359, https://arxiv.org/abs/2001.07359
- Grimm, Weidemuller and Ovchinnikov 2000, https://arxiv.org/abs/physics/9902072
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
