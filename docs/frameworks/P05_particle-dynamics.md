# P05, Particle dynamics (bead and atom in the computed potential)

Physics component. A bead or an atom is simulated inside the potential of the computed focal intensity map, and its position
trace is checked against two oracles: the Lorentzian power spectrum whose corner frequency is the trap stiffness over
$2\pi\gamma$, and the Boltzmann law of the potential.

| Item | Value |
|---|---|
| Module | `data-pipeline/pipeline/model/holo/core/dynamics.py` |
| Tests | `tests/engine/test_dynamics.py` |
| Used by | the Dynamics views, the C01 and C03 drivers (`data-pipeline/pipeline/stages/dynamics.py`) |

## Purpose

A hologram is judged by what the trapped particle does. The dynamics module closes that loop without a separate physics
code: it reads the same intensity map the metrics read.

## Equations

**Bead (overdamped).** The potential is $U(r) = -U_0\, I(r)/I_{max}$ and the force $F = -\nabla U$ from a central-difference
gradient of the map, bilinearly interpolated (positions outside the grid use the border values). The Euler-Maruyama step is

$$x_{n+1} = x_n + \frac{\Delta t}{\gamma} F(x_n) + \sqrt{2 D\,\Delta t}\;\zeta_n, \qquad D = \frac{k_B T}{\gamma},\ \zeta_n \sim \mathcal{N}(0,1)$$

(`bead_trajectory`, line 118). The design choice is $\Delta t \le \tau/20$ with $\tau = \gamma/\kappa$; the oracle test uses
$\tau/40$. The drag is Stokes, $\gamma = 6\pi\eta r$.

**Atom (underdamped).** $m\,a = F$ with velocity Verlet, an optional heating kick (a Gaussian velocity kick of rms
`kick_m_per_s` per step, a design choice, not a source claim) and a thermal initial velocity $\sqrt{k_B T/m}$ per axis
(`atom_trajectory`, line 140).

**Spectrum.** The thermal Lorentzian of Tolic-Norrelykke et al. 2006 (Eqs. 4 to 8, https://arxiv.org/abs/physics/0603037 ) is

$$P(f) = \frac{D}{2\pi^2 (f^2 + f_c^2)}, \qquad f_c = \frac{\kappa}{2\pi\gamma}$$

which integrates over positive and negative $f$ to $k_B T/\kappa$. The one-sided periodogram of Hann-windowed segments used here is
twice that, $P_1(f) = D/(\pi^2(f^2 + f_c^2))$ (derived from the same integral). `psd` (line 166) averages segments;
`fit_lorentzian` (line 191) fits $1/P = a + b f^2$ by weighted linear least squares (weights $P^2$, because the relative error of an
averaged periodogram bin is constant), giving $f_c = \sqrt{a/b}$ and $D = \pi^2/b$. `boltzmann_check` (line 213) compares the
position histogram with $\exp(-U/k_B T)$.

## Implementation

- Entrypoints: `dynamics.bead_trajectory`, `atom_trajectory`, `psd`, `fit_lorentzian`, `boltzmann_check`, `BeadParams`, `AtomParams`.
- Draw order from the portable generator is part of the contract so that the TypeScript port draws the same stream: the atom's
  initial velocity (2 normals), then the noise or kick block `normal_array(2 * n_steps)` reshaped to `(n_steps, 2)`; the block is
  always drawn, so the stream does not depend on whether the kick is zero.
- Case settings: C01 bead of radius 0.5 um, 131072 steps of 5e-5 s; C03 atom of 87 amu, 50000 steps of 1e-7 s, 50 uK
  (`data-pipeline/pipeline/cases/library.py`, lines 130 to 132 and 172 to 173). In the bake driver the fit uses a band of 5 corner
  frequencies and 2048-sample segments, because the Lorentzian is the model near the corner, not up to the Nyquist frequency.

## Acceptance criterion and test

The simulated bead's power spectrum recovers the input corner frequency within 10 percent
(`tests/engine/test_dynamics.py::test_corner_frequency_oracle`); equipartition and the Boltzmann law hold
(`::test_equipartition_and_boltzmann`); the atom oscillates at the harmonic frequency with the expected energy
(`::test_atom_harmonic_frequency_and_energy`).

## Measured values (DinHot measurements)

| Quantity | Measured | Conditions |
|---|---|---|
| Fitted over input corner frequency | 1.024, 1.058, 1.035 (limit 1.10) | $\kappa$ = 1e-5 N/m, 0.5 um bead, $\Delta t = \tau/40$, 2^17 steps, 64 segments, seeds 1, 2, 3 (engine test run of 2026-10-28) |
| Diffusion constant | within 15 percent of input | same run |
| Bake driver corner-frequency ratio | 0.97 to 1.07 | five seeds, with planted test methods (producer development run); the canonical bake restates it |

## Limits

- The linearised Lorentzian fit is biased at low segment counts (Norrelykke and Flyvbjerg 2010, https://arxiv.org/abs/0906.1708 ,
  abstract only read; UNVERIFIED which correction applies). The oracle test bounds the effect at 10 percent for the run it uses.
- The bead is overdamped (no inertia); the atom has no collisional damping.
- The stiffness magnitude inherits the vacuum prefactor caveat of [P04](P04_trap-physics.md).

## References

- Tolic-Norrelykke et al. 2006, https://arxiv.org/abs/physics/0603037
- Norrelykke and Flyvbjerg 2010, https://arxiv.org/abs/0906.1708
