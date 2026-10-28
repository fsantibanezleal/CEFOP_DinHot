// The live lane: a TypeScript port of data-pipeline/pipeline/model/sir.py, step for step (forward Euler, the same
// step, the same order of operations, the same clamps), so the browser re-runs a case with the reader's parameters.
// sir.parity.test.ts holds it to the traces the Python engine baked (T12): a change to either engine that is not
// made to the other fails the web's tests.
import type { CaseParams } from '../lib/contract.types';

export const DT = 0.25;

export interface SirInput extends CaseParams {
  /** A variant: the share of the susceptible population immunised at t = 0 (moved to R). Live lane only. */
  vaccinated?: number;
}

export interface SirRun {
  t: number[];
  S: number[];
  I: number[];
  R: number[];
  peakI: number;
  tPeak: number;
  /** Infections over the horizon as a share of the population (immunised people are not infections). */
  attackRate: number;
}

export function simulate(p: SirInput, dt = DT): SirRun {
  const steps = Math.max(1, Math.round(p.days / dt));
  let S = p.N - p.I0;
  let I = p.I0;
  let R = 0;
  const v = p.vaccinated ?? 0;
  if (v > 0) {
    const moved = S * v;
    S -= moved;
    R += moved;
  }
  const immunised = R;
  const betaOverN = p.N > 0 ? p.beta / p.N : 0;
  const t = [0];
  const Ss = [S];
  const Is = [I];
  const Rs = [R];
  for (let k = 1; k <= steps; k += 1) {
    const newInf = betaOverN * S * I * dt;
    const newRec = p.gamma * I * dt;
    S = Math.max(0, S - newInf);
    I = Math.max(0, I + newInf - newRec);
    R = R + newRec;
    t.push(k * dt);
    Ss.push(S);
    Is.push(I);
    Rs.push(R);
  }
  let peak = 0;
  for (let k = 1; k < Is.length; k += 1) if (Is[k] > Is[peak]) peak = k;
  return {
    t,
    S: Ss,
    I: Is,
    R: Rs,
    peakI: Is[peak],
    tPeak: t[peak],
    attackRate: p.N > 0 ? (Rs[Rs.length - 1] - immunised) / p.N : 0,
  };
}

/** The run's values at the trace's times (both grids are multiples of the step), for overlays and parity. */
export function atTimes(run: SirRun, times: number[], dt = DT): { S: number[]; I: number[]; R: number[] } {
  const idx = times.map((x) => Math.min(run.t.length - 1, Math.round(x / dt)));
  return { S: idx.map((i) => run.S[i]), I: idx.map((i) => run.I[i]), R: idx.map((i) => run.R[i]) };
}

/**
 * The final size of an SIR epidemic seeded by a vanishing infection in a fully susceptible population: the share z
 * that is ever infected solves z = 1 - exp(-R0 z) (Kermack and McKendrick 1927; Miller 2012). For R0 <= 1 it is 0.
 */
export function finalSize(r0: number): number {
  if (!(r0 > 1)) return 0;
  let z = 1;
  for (let k = 0; k < 60; k += 1) {
    const f = z - 1 + Math.exp(-r0 * z);
    const df = 1 - r0 * Math.exp(-r0 * z);
    const next = z - f / df;
    if (Math.abs(next - z) < 1e-14) return next;
    z = next;
  }
  return z;
}
