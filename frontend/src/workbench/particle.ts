// V4, the bead in its trap: the pure parts of the dynamics view (the time of a frame, the window of the zoomed map, the three callouts)
// and the link that opens the App on a case, a method and a view. Nothing here reads the DOM, so each rule is tested in node.
import { formatNumber, type SceneCalloutDef } from '@fasl-work/caos-app-shell';

type Lang = 'en' | 'es';

/** The case of the bake that carries a particle simulation (particle.test.ts reads its manifest): where a case without one sends the reader. */
export const DYNAMICS_CASE = 'C01_square_grid';

/** Micrometres with the micro sign in a unit the engine or the bake wrote with "um". */
export const unitText = (u: string): string => u.replace(/\bum\b/g, 'µm');

export interface Trace2D {
  xUm: ArrayLike<number>;
  yUm: ArrayLike<number>;
  dtS: number;
}

/** The time of a frame, in milliseconds. */
export const frameTimeMs = (frame: number, dtS: number): number => frame * dtS * 1e3;

/** The bead's displacement from its trap centre at a frame (holds at the last frame past the end). */
export function framePoint(tr: Trace2D, frame: number): { xUm: number; yUm: number } {
  const k = Math.max(0, Math.min(Math.min(tr.xUm.length, tr.yUm.length) - 1, frame));
  return { xUm: tr.xUm[k], yUm: tr.yUm[k] };
}

/** Cells shown either side of the trap the bead sits in: the bead's own radius in cells and three around it, never fewer than three. */
export const beadWindow = (radiusUm: number, binUm: number): number => Math.max(3, Math.round(radiusUm / binUm) + 3);

export interface ParticleCalloutArgs {
  tr: { fcHz: number; stiffness: { value: number; unit: string } };
  /** The depth of the simulated trap at the baked power, or null when the case holds none. */
  depth: { value: number; unit: string } | null;
  /** The rail power over the baked power: depth is proportional to the power. */
  depthScale: number;
  particle: 'bead' | 'atom';
  lang: Lang;
  /** The narrow layout stacks the map over the charts, so the anchors move with it. */
  narrow: boolean;
}

/** The stiffness (or the radial frequency of an atom), the corner frequency and the depth, each pinned to the mark of the picture that shows it. */
export function particleCallouts(a: ParticleCalloutArgs): SceneCalloutDef[] {
  const f = (v: number, d: number) => formatNumber(v, a.lang, { decimals: d });
  const bead = a.particle === 'bead';
  // the bead sits at the centre of the map (left half, or the top block when narrow); the spectrum is the lower chart of the right half
  const atBead = a.narrow ? { x: 0.5, y: 0.3 } : { x: 0.25, y: 0.55 };
  const atSpectrum = a.narrow ? { x: 0.5, y: 0.9 } : { x: 0.75, y: 0.8 };
  const out: SceneCalloutDef[] = [
    {
      id: 'kappa',
      eyebrow: bead ? { en: 'STIFFNESS', es: 'RIGIDEZ' } : { en: 'RADIAL FREQUENCY', es: 'FRECUENCIA RADIAL' },
      value: f(a.tr.stiffness.value, bead ? 2 : 1),
      unit: unitText(a.tr.stiffness.unit),
      state: 'selected',
      anchor: { x: atBead.x - 0.04, y: atBead.y },
      source: bead
        ? { en: 'From the corner frequency of the bead', es: 'De la frecuencia de corte de la microesfera' }
        : { en: 'Of the atom in the trap', es: 'Del átomo en la trampa' },
    },
    {
      id: 'fc',
      eyebrow: { en: 'CORNER FREQUENCY', es: 'FRECUENCIA DE CORTE' },
      value: f(a.tr.fcHz, 1),
      unit: 'Hz',
      state: 'normal',
      anchor: atSpectrum,
      source: { en: 'Fitted to the power spectrum', es: 'Ajustada al espectro de potencia' },
    },
  ];
  if (a.depth) {
    out.push({
      id: 'depth',
      eyebrow: { en: 'TRAP DEPTH', es: 'PROFUNDIDAD' },
      value: f(a.depth.value * a.depthScale, 0),
      unit: unitText(a.depth.unit),
      state: 'normal',
      anchor: { x: atBead.x + 0.04, y: atBead.y },
      source: a.depthScale === 1 ? { en: 'At the power of the simulation', es: 'Con la potencia de la simulación' } : { en: 'Scaled to the rail power', es: 'Reescalada a la potencia del panel' },
    });
  }
  return out;
}

/** The URL of the App on a case, a method and a view (`base` is the site's base path, as Vite writes it). */
export function appHref(base: string, q: { case: string; method?: string; view?: string }): string {
  const p = new URLSearchParams();
  p.set('case', q.case);
  if (q.method) p.set('method', q.method);
  if (q.view) p.set('view', q.view);
  return `${base.endsWith('/') ? base : `${base}/`}app/?${p.toString()}`;
}
