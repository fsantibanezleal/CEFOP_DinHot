"""EXAMPLE cases spanning CATEGORIES (the domain problem-type taxonomy). Replace per product with your real,
varied coverage matrix. Each case: id, category, params, expected band (what a domain expert should see),
real|synthetic flag. Includes a negative/degenerate CONTROL the engine must handle without crashing."""
from __future__ import annotations

from dataclasses import dataclass

from ..io.schema import SIRParams


Text = dict  # {"en": str, "es": str}: every reader-facing string is bilingual at the source (ADR-0011)


@dataclass(frozen=True)
class Case:
    id: str
    title: Text
    category: Text
    params: SIRParams
    expected_band: Text
    real_or_synthetic: str
    # The checked form of expected_band: a range per result metric (peak_I, t_peak, attack_rate). The bake fails on
    # a value outside it (core/expect.py); the prose above must say the same thing in words.
    expect: dict


# The case the App opens on (a deep link ?case=<id> overrides it).
DEFAULT_CASE = "EX02_epidemic"

_OUTBREAK = {"en": "Outbreak regimes", "es": "Regímenes de brote"}
_CONTROL = {"en": "Controls", "es": "Controles"}

CASES: list[Case] = [
    Case("EX01_subcritical", {"en": "Sub-critical spread", "es": "Propagación subcrítica"}, _OUTBREAK,
         SIRParams("EX01_subcritical", beta=0.18, gamma=0.25, N=100_000, I0=50),
         {"en": "No outbreak: the peak stays near the initial infections and the attack rate near zero.",
          "es": "Sin brote: el pico se queda cerca de los contagios iniciales y la tasa de ataque cerca de cero."},
         "synthetic", {"peak_I": (50.0, 60.0), "attack_rate": (0.0, 0.005)}),
    Case("EX02_epidemic", {"en": "Epidemic", "es": "Epidemia"}, _OUTBREAK,
         SIRParams("EX02_epidemic", beta=0.55, gamma=0.20, N=100_000, I0=50),
         {"en": "One clear peak in the first month; an attack rate above 0.9, as the final size predicts for R0 = 2.75.",
          "es": "Un pico claro en el primer mes; una tasa de ataque sobre 0,9, como predice el tamaño final para R0 = 2,75."},
         "synthetic", {"t_peak": (15.0, 35.0), "attack_rate": (0.90, 0.95)}),
    Case("EX03_fast_burn", {"en": "Fast burn", "es": "Combustión rápida"}, _OUTBREAK,
         SIRParams("EX03_fast_burn", beta=1.20, gamma=0.20, N=100_000, I0=100),
         {"en": "An early, sharp peak; an attack rate close to 1.",
          "es": "Un pico temprano y agudo; una tasa de ataque cercana a 1."},
         "synthetic", {"t_peak": (5.0, 15.0), "attack_rate": (0.99, 1.0)}),
    Case("EX04_slow_spread", {"en": "Slow spread", "es": "Propagación lenta"}, _OUTBREAK,
         SIRParams("EX04_slow_spread", beta=0.30, gamma=0.25, N=100_000, I0=50),
         {"en": "A broad, low peak late in the horizon; the epidemic is still running when the horizon ends.",
          "es": "Un pico amplio y bajo, tarde en el horizonte; la epidemia sigue activa cuando termina el horizonte."},
         "synthetic", {"t_peak": (70.0, 130.0), "attack_rate": (0.20, 0.35)}),
    Case("CTRL_degenerate", {"en": "No initial infection", "es": "Sin contagio inicial"}, _CONTROL,
         SIRParams("CTRL_degenerate", beta=0.40, gamma=0.20, N=100_000, I0=0),
         {"en": "No dynamics: the engine must run and report a peak of 0 and an attack rate of 0.",
          "es": "Sin dinámica: el motor debe correr y reportar un pico de 0 y una tasa de ataque de 0."},
         "synthetic", {"peak_I": (0.0, 0.0), "attack_rate": (0.0, 0.0)}),
]
