// The published numbers the cases are set against, each with its source and the conditions it holds under. These are the only numbers of
// the Experiments page that are typed rather than read from an artifact, because a published result is not a result of this build.
// Where the case record differs from the source's conditions the difference is stated beside the number (a published value is never
// shown as if it had been measured under this build's conditions). Transcribed from the anchor lines the manifests carry
// (`anchor.source`) and from the validation-anchor sections of the case cards (`docs/cases/*/C*.md`), which quote the sources;
// the papers themselves were read only as far as those cards record (the section and figure numbers are the cards'), so a value not
// marked otherwise is UNVERIFIED against the paper's full text in this unit.
import type { Text } from '../../lib/contract.types';

export interface Published {
  /** Reference id in `citations/methodology.ts` or `citations/experiments.ts`. */
  cite: string;
  /** The conditions the number holds under. */
  conditions: Text;
}

/** Nogrette et al. 2014 section III.E and Fig. 9: the camera loop on a flat beam, 768 by 768 pixels. */
export const NOGRETTE_FEEDBACK = {
  cite: 'nogrette2014',
  initialPct: 19,
  finalPct: 1.4,
  steps: 20,
  gain: 0.7,
  conditions: {
    en: 'camera loop of Nogrette et al. 2014, section III.E and Fig. 9: 19 percent rms before and 1.4 percent after 20 iterations at gain 0.7, on a flat beam and a 768 by 768 pixel SLM',
    es: 'lazo de cámara de Nogrette et al. 2014, sección III.E y fig. 9: 19 por ciento rms antes y 1,4 por ciento después de 20 iteraciones con ganancia 0,7, con haz plano y un SLM de 768 por 768 píxeles',
  },
} as const;

/** Kim et al. 2019: three camera steps on a large array. */
export const KIM_FEEDBACK = {
  cite: 'kim2019',
  initialPct: 22,
  finalPct: 1.4,
  steps: 3,
  conditions: {
    en: 'Kim et al. 2019, Optics Letters 44, 3178: 22 percent before and 1.4 percent after three steps in the histogram of one run (1.59 plus or minus 0.18 percent over 8 ensembles); the array size reference is Ebadi et al. 2021',
    es: 'Kim et al. 2019, Optics Letters 44, 3178: 22 por ciento antes y 1,4 por ciento después de tres pasos en el histograma de una corrida (1,59 más o menos 0,18 por ciento sobre 8 conjuntos); la referencia del tamaño de la matriz es Ebadi et al. 2021',
  },
} as const;

/** Kim et al. 2019: the disordered set of 819 foci after five adaptive steps (context for C13, not a band: the source used a flat beam and a 768-pixel device). */
export const KIM_DISORDERED = {
  cite: 'kim2019',
  finalPct: 1.2,
  spreadPct: 0.11,
  steps: 5,
  foci: 819,
  pixels: 768,
  conditions: {
    en: 'Kim et al. 2019, Optics Letters 44, 3178: 819 disordered foci, 1.2 percent after five adaptive steps, with a flat beam and a 768-pixel device',
    es: 'Kim et al. 2019, Optics Letters 44, 3178: 819 focos desordenados, 1,2 por ciento tras cinco pasos adaptativos, con un haz plano y un dispositivo de 768 píxeles',
  },
} as const;

/** Nogrette et al. 2014 section III.D: the aberration correction. */
export const NOGRETTE_ABERRATION = {
  cite: 'nogrette2014',
  beforeWaves: 0.15,
  afterWaves: 0.014,
  depthGainPct: 50,
  conditions: {
    en: 'Nogrette et al. 2014, section III.D: wavefront rms from 0.15 to 0.014 waves, trap depth up by about 50 percent, on their instrument',
    es: 'Nogrette et al. 2014, sección III.D: rms del frente de onda de 0,15 a 0,014 ondas, profundidad de trampa mayor en cerca de 50 por ciento, en su instrumento',
  },
} as const;

/** Schroff et al. 2023: the shaped disc with a crosstalk model. */
export const SCHROFF_DISC = {
  cite: 'schroff2023',
  errorBelowPct: 2,
  effLowPct: 15,
  effHighPct: 40,
  conditions: {
    en: 'Schroff et al. 2023, Scientific Reports 13, 3252: RMS error below 2 percent with efficiency 15 to 40 percent, on their device with a measured crosstalk kernel',
    es: 'Schroff et al. 2023, Scientific Reports 13, 3252: error RMS bajo 2 por ciento con eficiencia de 15 a 40 por ciento, en su dispositivo con un núcleo de diafonía medido',
  },
} as const;

/** Polin et al. 2005: the 51-trap array after direct search. */
export const POLIN_ARRAY = {
  cite: 'polin2005',
  withinPct: 5,
  conditions: {
    en: 'Polin et al. 2005, Optics Express 13, 5831: 51 traps with 12 vortices of charge 8 within 5 percent after direct search; the paper does not state here which spread statistic it uses (UNVERIFIED)',
    es: 'Polin et al. 2005, Optics Express 13, 5831: 51 trampas con 12 vórtices de carga 8 dentro de 5 por ciento tras la búsqueda directa; aquí no se precisa qué estadístico de dispersión usa el artículo (SIN VERIFICAR)',
  },
} as const;

/** Di Leonardo et al. 2007 Table 1 at 8 Fourier units: efficiency and uniformity of four baselines (case card of C12). */
export const DILEONARDO_TABLE: { method: string; name: Text; efficiency: number; uniformity: number }[] = [
  { method: 'M01', name: { en: 'superposition', es: 'superposición' }, efficiency: 0.29, uniformity: 0.01 },
  { method: 'M02', name: { en: 'random superposition', es: 'superposición aleatoria' }, efficiency: 0.69, uniformity: 0.01 },
  { method: 'M04', name: { en: 'Gerchberg-Saxton', es: 'Gerchberg-Saxton' }, efficiency: 0.94, uniformity: 0.6 },
  { method: 'M06', name: { en: 'weighted GS', es: 'GS ponderado' }, efficiency: 0.93, uniformity: 0.99 },
];

export const DILEONARDO = {
  cite: 'dileonardo2007',
  /** The pixels per side of the published SLM (the card of C12: a flat beam at 768 by 768 pixels). */
  pixels: 768,
  conditions: {
    en: 'Di Leonardo, Ianni and Ruocco 2007, Optics Express 15, 1913, Table 1: a 10 by 10 task at 8 Fourier units on a flat beam and 768 by 768 pixels',
    es: 'Di Leonardo, Ianni y Ruocco 2007, Optics Express 15, 1913, tabla 1: una tarea de 10 por 10 a 8 unidades de Fourier con haz plano y 768 por 768 píxeles',
  },
} as const;

/** Constants of the code that the metric equations quote (not results): where each lives. */
export const CODE_CONSTANTS = {
  /** `REL_STD_CAP` of `core/score.py`: the units domain of the spread slot, so a shaped target's signal error is clipped here. */
  relStdCapPct: 1000,
  /** `REL` and `SEEDS` of `ranges.py`: the width and the seed count of a measured range. */
  rangeRelFraction: 0.1,
  rangeSeeds: 3,
  /** `MIN_DENOMINATOR` of `stages/feedback.py`: keeps the feedback factor finite for gains above 1. */
  feedbackMinDenominator: 0.1,
} as const;
