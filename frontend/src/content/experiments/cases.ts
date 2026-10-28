// The written content of each case on the Experiments page: its question, its setup and what the bake measured against its anchor. A
// paragraph is a bilingual TEMPLATE whose `{token}` placeholders are filled at run time from the committed artifacts (`vals`), so the page
// never restates a number by hand: the test `experiments.test.ts` fails a template that holds a digit of its own, a token no `vals`
// provides, or a token left unused. The questions, the setups and the anchors are transcribed from the case cards (`docs/cases/*/C*.md`,
// section Question, Why this case exists, Expected results, Validation anchor and Notes) and from the manifests' anchor lines; the
// published numbers are in `anchors.ts` with their sources and conditions.
import type { Text } from '../../lib/contract.types';
import {
  DILEONARDO,
  DILEONARDO_TABLE,
  KIM_DISORDERED,
  KIM_FEEDBACK,
  NOGRETTE_ABERRATION,
  NOGRETTE_FEEDBACK,
  POLIN_ARRAY,
  SCHROFF_DISC,
} from './anchors';
import {
  aberrationRmsWaves,
  feedbackSteps,
  inside,
  isShaped,
  latticeUm,
  methodIds,
  particleOracle,
  planesUm,
  pupilDepthOfField,
  rangeOf,
  rangeScore,
  refOf,
  trapCount,
  validityFlags,
  type CaseView,
  type Metric,
} from './data';

export type Lang = 'en' | 'es';

/** Number formatters bound to the displayed language (the shell's `formatNumber`). */
export interface Fmt {
  lang: Lang;
  /** The ids of the cases of the index (a case the page reads about but does not own, such as the disordered set, is looked up here). */
  caseIds: string[];
  /** A number in the language, with significant `digits` (default 3) or fixed `decimals`. */
  n: (v: number | null | undefined, o?: { digits?: number; decimals?: number; grouping?: boolean }) => string;
  /** A percent value (already in percent) joined to its sign by a no-break space. */
  pct: (v: number | null | undefined, o?: { digits?: number; decimals?: number; grouping?: boolean }) => string;
}

/** One row of the table of a case: a quantity, the published value, the range the bake checked, what the bake measured and how they compare. */
export interface Row {
  label: string;
  published: string | null;
  range: string | null;
  here: string;
  reading: string | null;
}

export interface CaseText {
  /** The question of the case card, one sentence, no number. */
  question: Text;
  /** Setup paragraph template. */
  setup: Text;
  /** Result paragraph template (what the bake measured against the anchor). */
  result: Text;
  vals: (v: CaseView, f: Fmt) => Record<string, string>;
  /** Rows of the case's table beyond the generic ones (the published anchor numbers). */
  extra?: (v: CaseView, f: Fmt) => Row[];
}

const DASH = '-';
const M = (v: CaseView, id: string) => v.manifest.methods[id];
const pick = (t: Text, lang: Lang) => t[lang];

/** The values every case shares. */
export function common(v: CaseView, f: Fmt): Record<string, string> {
  const m = v.manifest;
  const s = m.params.setup;
  const ref = refOf(m);
  const ids = methodIds(m);
  const scored = ids.map((id) => ({ id, ...rangeScore(m, id) })).filter((x) => x.of > 0);
  return {
    n: f.n(trapCount(m), { decimals: 0 }),
    lat: f.n(latticeUm(m), { digits: 4 }),
    wl: f.n(s.wavelength_nm, { digits: 4 }),
    focal: f.n(s.focal_mm, { digits: 3 }),
    na: f.n(s.na, { digits: 2 }),
    npix: f.n(s.n_pix, { decimals: 0 }),
    pitch: f.n(s.pitch_um, { digits: 3 }),
    fu: f.n(latticeUm(m) !== null ? (latticeUm(m) as number) / (s.pad * v.trace.grid.bin_um) : undefined, { digits: 3 }),
    seed: f.n(m.seed, { decimals: 0, grouping: false }),
    nm: f.n(ids.length, { decimals: 0 }),
    ref: m.params.reference_method,
    iters: f.n(m.params.budget.iterations, { decimals: 0 }),
    refEff: f.n(ref?.efficiency, { decimals: 3 }),
    refU: f.n(ref?.uniformity, { decimals: 3 }),
    refSd: f.n(ref?.rel_std_pct, { digits: 3 }),
    best: v.trace.summary.best_method,
    okAll: f.n(scored.filter((x) => x.ok === x.of).length, { decimals: 0 }),
    ofAll: f.n(scored.length, { decimals: 0 }),
  };
}

/** The vortex traps (charge other than zero) and the plain ones of a trap target, and the largest charge. */
function vortices(v: CaseView, f: Fmt): Record<string, string> {
  const t = 'traps' in v.manifest.params.target ? v.manifest.params.target.traps : [];
  const charged = t.filter((x) => x.charge !== 0);
  return {
    nVort: f.n(charged.length, { decimals: 0 }),
    nPlain: f.n(t.length - charged.length, { decimals: 0 }),
    charge: f.n(charged.reduce((m, x) => Math.max(m, Math.abs(x.charge)), 0), { decimals: 0 }),
  };
}

/** The sentence about the scalar model's validity, read from the flags of the manifest. */
function validity(v: CaseView, f: Fmt): string {
  const es = f.lang === 'es';
  return validityFlags(v.manifest).length
    ? es
      ? 'El manifiesto marca el modelo escalar como usado más allá de su validez a esta apertura, así que los números describen el holograma escalar y no un foco vectorial.'
      : 'The manifest flags the scalar model as used beyond its validity at this aperture, so the numbers describe the scalar hologram and not a vectorial focus.'
    : es
      ? 'El manifiesto no marca ningún límite de validez del modelo escalar en este caso.'
      : 'The manifest raises no validity flag for the scalar model in this case.';
}

const metricOf = (v: CaseView, id: string, k: Metric): number | undefined => M(v, id)?.[k];
const nfmt = (f: Fmt, x: number | undefined, o?: { digits?: number; decimals?: number }) => (x === undefined ? DASH : f.n(x, o));

/** The loop's first, one-step and last measured spread of a case with a camera loop. */
function loop(v: CaseView) {
  const s = feedbackSteps(v.trace);
  return { first: s[0]?.rel_std_pct, one: s[1]?.rel_std_pct, last: s[s.length - 1]?.rel_std_pct, steps: s.length ? s.length - 1 : 0 };
}

/** Smallest value of a metric over the methods of a case, with the method that holds it. */
function lowest(v: CaseView, k: Metric): { id: string; value: number } | null {
  let best: { id: string; value: number } | null = null;
  for (const id of methodIds(v.manifest)) {
    const x = metricOf(v, id, k);
    if (x !== undefined && (best === null || x < best.value)) best = { id, value: x };
  }
  return best;
}

const ratioText = (f: Fmt, here: number | undefined, pub: number): string | null =>
  here === undefined ? null : f.lang === 'es' ? `${f.n(here / pub, { digits: 3 })} veces el valor publicado` : `${f.n(here / pub, { digits: 3 })} times the published value`;

const signed = (f: Fmt, d: number, o: { decimals: number }): string => `${d >= 0 ? '+' : '-'}${f.n(Math.abs(d), o)}`;

export const CASES: Record<string, CaseText> = {
  C01_square_grid: {
    question: {
      en: 'Can a small square array of equal traps be made, and does a bead in the central trap behave as the computed stiffness says?',
      es: '¿Puede hacerse una matriz cuadrada pequeña de trampas iguales, y se comporta una esfera en la trampa central como dice la rigidez calculada?',
    },
    setup: {
      en: 'The case places {n} equal traps on a square lattice with {lat} um spacing, made with a beam of {wl} nm through a lens of {focal} mm focal length and numerical aperture {na}, on an SLM of {npix} by {npix} pixels. {nm} methods run on it with the seed {seed} and a budget of {iters} iterations, and the reference method is {ref}. A bead of {beadR} um radius and refractive index {nBead} in the central trap, driven at {power} mW, tests the hologram through the particle it holds, and an emulated camera with a gain error of {gainRms} rms closes a loop of {fbGain} gain over {steps} steps.',
      es: 'El caso coloca {n} trampas iguales en una red cuadrada con {lat} um de separación, hechas con un haz de {wl} nm a través de un lente de {focal} mm de distancia focal y apertura numérica {na}, sobre un SLM de {npix} por {npix} píxeles. Corren {nm} métodos con la semilla {seed} y un presupuesto de {iters} iteraciones, y el método de referencia es {ref}. Una esfera de {beadR} um de radio e índice de refracción {nBead} en la trampa central, impulsada a {power} mW, pone a prueba el holograma por la partícula que sostiene, y una cámara emulada con un error de ganancia de {gainRms} rms cierra un lazo de ganancia {fbGain} durante {steps} pasos.',
    },
    result: {
      en: 'The reference method {ref} reaches an efficiency of {refEff} and a uniformity of {refU}, a relative standard deviation of {refSd} percent, and the bake names {best} as the most uniform method among those that keep at least half the best efficiency. The camera loop takes the measured spread from {fb0} percent to {fb1} percent after one step and {fbN} percent after {steps} steps. The bead\'s spectrum has a corner frequency of {fcM} Hz against {fcE} Hz expected from the stiffness, a ratio of {fcR}. {okAll} of {ofAll} methods with checked ranges sit inside all of them. The published anchor of this case is an occupancy of about one half per trap, which this build does not simulate, so no published number is compared here.',
      es: 'El método de referencia {ref} alcanza una eficiencia de {refEff} y una uniformidad de {refU}, con una desviación estándar relativa de {refSd} por ciento, y la generación nombra a {best} como el método más uniforme entre los que conservan al menos la mitad de la mejor eficiencia. El lazo de cámara baja la dispersión medida de {fb0} por ciento a {fb1} por ciento tras un paso y a {fbN} por ciento tras {steps} pasos. El espectro de la esfera tiene una frecuencia de corte de {fcM} Hz frente a {fcE} Hz esperados por la rigidez, una razón de {fcR}. {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos. El ancla publicada de este caso es una ocupación de cerca de la mitad por trampa, que esta versión no simula, así que aquí no se compara ningún número publicado.',
    },
    vals: (v, f) => {
      const p = v.manifest.params;
      const L = loop(v);
      const o = particleOracle(v);
      return {
        ...common(v, f),
        beadR: f.n(p.dynamics?.bead_radius_um, { digits: 2 }),
        nBead: f.n(p.dynamics?.n_particle, { digits: 3 }),
        power: f.n(p.dynamics?.power_mw, { digits: 3 }),
        gainRms: f.n(p.feedback?.camera.gain_rms, { digits: 2 }),
        fbGain: f.n(p.feedback?.gain, { digits: 2 }),
        steps: f.n(L.steps, { decimals: 0 }),
        fb0: f.n(L.first, { digits: 3 }),
        fb1: f.n(L.one, { digits: 3 }),
        fbN: f.n(L.last, { digits: 3 }),
        fcM: f.n(o?.measured, { digits: 4 }),
        fcE: f.n(o?.expected, { digits: 4 }),
        fcR: f.n(o?.ratio, { digits: 3 }),
      };
    },
  },

  C02_grid_feedback: {
    question: {
      en: 'How far can a camera feedback loop bring the depth spread of a large square array, and how fast?',
      es: '¿Hasta dónde puede un lazo de realimentación de cámara bajar la dispersión de profundidad de una matriz cuadrada grande, y con qué rapidez?',
    },
    setup: {
      en: 'The case places {n} equal traps on a square lattice with {lat} um spacing, with the optics of the atom setup: {wl} nm, a lens of {focal} mm and numerical aperture {na}, an SLM of {npix} by {npix} pixels. The emulated camera has a gain error of {gainRms} rms and a readout noise of {noise}, the loop has a gain of {fbGain} and {steps} steps, and {nm} methods run with the seed {seed}. The reference method is {ref}, whose hologram starts the loop; the closed-loop weighted method of the ladder is run on the same camera as a method of its own.',
      es: 'El caso coloca {n} trampas iguales en una red cuadrada con {lat} um de separación, con la óptica del montaje de átomos: {wl} nm, un lente de {focal} mm y apertura numérica {na}, un SLM de {npix} por {npix} píxeles. La cámara emulada tiene un error de ganancia de {gainRms} rms y un ruido de lectura de {noise}, el lazo tiene una ganancia de {fbGain} y {steps} pasos, y corren {nm} métodos con la semilla {seed}. El método de referencia es {ref}, cuyo holograma inicia el lazo; el método ponderado de lazo cerrado de la escalera corre sobre la misma cámara como un método propio.',
    },
    result: {
      en: 'The measured spread of the traps falls from {fb0} percent before the loop to {fbN} percent after {steps} steps, a reduction of {fold} times, and the first step alone reaches {fb1} percent. The reference method {ref} has an efficiency of {refEff} and a uniformity of {refU} at the end of the loop, and the bake names {best} as the most uniform method. The published result is {pubInit} percent rms falling to {pubFinal} percent in {pubSteps} iterations at gain {pubGain}, so the loop here ends {below} the published value. The emulated camera has a readout noise of {noise} and a blur of {blur} bins, and these are the errors that set the floor of a real loop when they are not zero, so this result shows that the loop works against the stated errors and is not a prediction for an instrument.',
      es: 'La dispersión medida de las trampas baja de {fb0} por ciento antes del lazo a {fbN} por ciento tras {steps} pasos, una reducción de {fold} veces, y el primer paso solo alcanza {fb1} por ciento. El método de referencia {ref} tiene una eficiencia de {refEff} y una uniformidad de {refU} al final del lazo, y la generación nombra a {best} como el método más uniforme. El resultado publicado es {pubInit} por ciento rms que baja a {pubFinal} por ciento en {pubSteps} iteraciones con ganancia {pubGain}, así que el lazo termina aquí {below} valor publicado. La cámara emulada tiene un ruido de lectura de {noise} y un desenfoque de {blur} bins, y éstos son los errores que fijan el piso de un lazo real cuando no son cero, de modo que este resultado muestra que el lazo funciona contra los errores declarados y no es una predicción para un instrumento.',
    },
    vals: (v, f) => {
      const p = v.manifest.params;
      const L = loop(v);
      const ratio = L.first !== undefined && L.last ? L.first / L.last : undefined;
      return {
        ...common(v, f),
        gainRms: f.n(p.feedback?.camera.gain_rms, { digits: 2 }),
        noise: f.n(p.feedback?.camera.noise_rms, { digits: 2 }),
        blur: f.n(p.feedback?.camera.blur_bins, { digits: 2 }),
        fbGain: f.n(p.feedback?.gain, { digits: 2 }),
        steps: f.n(L.steps, { decimals: 0 }),
        fb0: f.n(L.first, { digits: 3 }),
        fb1: f.n(L.one, { digits: 3 }),
        fbN: f.n(L.last, { digits: 3 }),
        fold: f.n(ratio, { digits: 3 }),
        pubInit: f.n(NOGRETTE_FEEDBACK.initialPct, { digits: 3 }),
        pubFinal: f.n(NOGRETTE_FEEDBACK.finalPct, { digits: 3 }),
        pubSteps: f.n(NOGRETTE_FEEDBACK.steps, { decimals: 0 }),
        pubGain: f.n(NOGRETTE_FEEDBACK.gain, { digits: 2 }),
        below: L.last !== undefined && L.last <= NOGRETTE_FEEDBACK.finalPct ? (f.lang === 'es' ? 'por debajo del' : 'below') : f.lang === 'es' ? 'por encima del' : 'above',
      };
    },
    extra: (v, f) => {
      const L = loop(v);
      const cond = pick(NOGRETTE_FEEDBACK.conditions, f.lang);
      return [
        { label: f.lang === 'es' ? 'Dispersión antes del lazo (porcentaje rms)' : 'Spread before the loop (percent rms)', published: `${f.n(NOGRETTE_FEEDBACK.initialPct, { digits: 3 })} (${cond})`, range: null, here: nfmt(f, L.first, { digits: 3 }), reading: ratioText(f, L.first, NOGRETTE_FEEDBACK.initialPct) },
        { label: f.lang === 'es' ? 'Dispersión tras el lazo (porcentaje rms)' : 'Spread after the loop (percent rms)', published: `${f.n(NOGRETTE_FEEDBACK.finalPct, { digits: 3 })} (${cond})`, range: null, here: nfmt(f, L.last, { digits: 3 }), reading: ratioText(f, L.last, NOGRETTE_FEEDBACK.finalPct) },
      ];
    },
  },

  C03_large_array: {
    question: {
      en: 'Does the large-array state of the art, phase-fixed weighted GS plus a few camera steps, hold on a large array, and what does an atom in one trap feel?',
      es: '¿Se sostiene en una matriz grande el estado del arte, GS ponderado de fase fija más unos pocos pasos de cámara, y qué siente un átomo en una trampa?',
    },
    setup: {
      en: 'The case places {n} equal traps on a square lattice with {lat} um spacing, with the optics of the atom setup ({wl} nm, {focal} mm, numerical aperture {na}, an SLM of {npix} by {npix} pixels). {nm} methods run on it, and the reference method is {ref}. The emulated camera has a gain error of {gainRms} rms, and the loop has a gain of {fbGain} and {steps} steps. A rubidium atom of {mass} mass units in one trap, at {power} mW, is integrated with a step of {dt} s to test the hologram through the frequency of its oscillation.',
      es: 'El caso coloca {n} trampas iguales en una red cuadrada con {lat} um de separación, con la óptica del montaje de átomos ({wl} nm, {focal} mm, apertura numérica {na}, un SLM de {npix} por {npix} píxeles). Corren {nm} métodos sobre ella, y el método de referencia es {ref}. La cámara emulada tiene un error de ganancia de {gainRms} rms, y el lazo tiene una ganancia de {fbGain} y {steps} pasos. Un átomo de rubidio de {mass} unidades de masa en una trampa, a {power} mW, se integra con un paso de {dt} s para probar el holograma por la frecuencia de su oscilación.',
    },
    result: {
      en: 'The measured spread falls from {fb0} percent to {fbN} percent in {steps} steps, against the published {pubInit} percent to {pubFinal} percent in {pubSteps} steps, so the ratio of the final spread to the published one is {fbRatio}. The reference method {ref} has an efficiency of {refEff} and a relative standard deviation of {refSd} percent before the loop. The atom oscillates at {fcM} Hz against {fcE} Hz expected from the curvature of the intensity, a ratio of {fcR}, in a trap {depth} uK deep. The lattice is regular; the disordered set of the anchor paper {disordered}.',
      es: 'La dispersión medida baja de {fb0} por ciento a {fbN} por ciento en {steps} pasos, frente a los {pubInit} por ciento a {pubFinal} por ciento publicados en {pubSteps} pasos, de modo que la razón de la dispersión final a la publicada es {fbRatio}. El método de referencia {ref} tiene una eficiencia de {refEff} y una desviación estándar relativa de {refSd} por ciento antes del lazo. El átomo oscila a {fcM} Hz frente a {fcE} Hz esperados por la curvatura de la intensidad, una razón de {fcR}, en una trampa de {depth} uK de profundidad. La red es regular; el conjunto desordenado del artículo ancla {disordered}.',
    },
    vals: (v, f) => {
      const p = v.manifest.params;
      const L = loop(v);
      const o = particleOracle(v);
      return {
        ...common(v, f),
        gainRms: f.n(p.feedback?.camera.gain_rms, { digits: 2 }),
        fbGain: f.n(p.feedback?.gain, { digits: 2 }),
        steps: f.n(L.steps, { decimals: 0 }),
        mass: f.n(p.dynamics?.mass_amu, { digits: 3 }),
        power: f.n(p.dynamics?.power_mw, { digits: 3 }),
        dt: f.n(p.dynamics?.dt_s, { digits: 2 }),
        fb0: f.n(L.first, { digits: 3 }),
        fbN: f.n(L.last, { digits: 3 }),
        fbRatio: f.n(L.last !== undefined ? L.last / KIM_FEEDBACK.finalPct : undefined, { digits: 3 }),
        pubInit: f.n(KIM_FEEDBACK.initialPct, { digits: 3 }),
        pubFinal: f.n(KIM_FEEDBACK.finalPct, { digits: 3 }),
        pubSteps: f.n(KIM_FEEDBACK.steps, { decimals: 0 }),
        fcM: f.n(o?.measured, { digits: 4 }),
        fcE: f.n(o?.expected, { digits: 4 }),
        fcR: f.n(o?.ratio, { digits: 3 }),
        depth: f.n(v.trace.dynamics?.depth.value, { digits: 4 }),
        // whether a case of the disordered set (C13) is in the index is read at run time
        disordered: f.caseIds.some((id) => /^C13/.test(id)) ? (f.lang === 'es' ? 'es un caso propio, C13' : 'is a case of its own, C13') : f.lang === 'es' ? 'no forma parte de este caso' : 'is not part of this case',
      };
    },
    extra: (v, f) => {
      const L = loop(v);
      const cond = pick(KIM_FEEDBACK.conditions, f.lang);
      return [
        { label: f.lang === 'es' ? 'Dispersión antes de los pasos (porcentaje)' : 'Spread before the steps (percent)', published: `${f.n(KIM_FEEDBACK.initialPct, { digits: 3 })} (${cond})`, range: null, here: nfmt(f, L.first, { digits: 3 }), reading: ratioText(f, L.first, KIM_FEEDBACK.initialPct) },
        { label: f.lang === 'es' ? 'Dispersión tras los pasos (porcentaje)' : 'Spread after the steps (percent)', published: `${f.n(KIM_FEEDBACK.finalPct, { digits: 3 })} (${cond})`, range: null, here: nfmt(f, L.last, { digits: 3 }), reading: ratioText(f, L.last, KIM_FEEDBACK.finalPct) },
      ];
    },
  },

  C13_disordered_array: {
    question: {
      en: 'Does the feedback-corrected uniformity of a lattice hold when the same kind of array sits at random positions with unequal neighbour distances, and which methods keep it?',
      es: '¿Se sostiene la uniformidad corregida por realimentación de una red cuando una matriz del mismo tipo está en posiciones al azar con distancias desiguales entre vecinas, y qué métodos la conservan?',
    },
    setup: {
      en: 'The case places {n} equal traps at random on integer bins of the Fourier plane, no two closer than {minSep} um and none farther than {half} um from the axis along either direction, with the optics of the atom setup ({wl} nm, {focal} mm, numerical aperture {na}, an SLM of {npix} by {npix} pixels) and a Gaussian input beam. The coordinates of the source are not published, so the draw is the product\'s own, made with a fixed seed, and the case is set against that paper as context and not as a reproduction. Every trap sits on a bin, so the same {nm} methods as the large lattice run on it, with the seed {seed} and a budget of {iters} iterations; the reference method is {ref}. The emulated camera has a gain error of {gainRms} rms and a readout noise of {noise}, and the loop has a gain of {fbGain} and {steps} steps.',
      es: 'El caso coloca {n} trampas iguales al azar sobre bins enteros del plano de Fourier, sin que dos estén más cerca que {minSep} um ni ninguna más lejos que {half} um del eje en cada dirección, con la óptica del montaje de átomos ({wl} nm, {focal} mm, apertura numérica {na}, un SLM de {npix} por {npix} píxeles) y un haz de entrada gaussiano. Las coordenadas de la fuente no están publicadas, así que el sorteo es propio del producto, hecho con una semilla fija, y el caso se contrasta con ese artículo como contexto y no como reproducción. Toda trampa cae sobre un bin, así que corren sobre él los mismos {nm} métodos que en la red grande, con la semilla {seed} y un presupuesto de {iters} iteraciones; el método de referencia es {ref}. La cámara emulada tiene un error de ganancia de {gainRms} rms y un ruido de lectura de {noise}, y el lazo tiene una ganancia de {fbGain} y {steps} pasos.',
    },
    result: {
      en: 'The reference method {ref} reaches an efficiency of {refEff} and a relative standard deviation of {refSd} percent in the ideal model, while weighted GS gives {sd06} percent and Gerchberg-Saxton {sd04} percent. The camera loop takes the measured spread from {fb0} percent to {fbN} percent in {steps} steps. Kim et al. 2019 report {pubFinal} percent after {pubSteps} adaptive steps on {pubFoci} disordered foci; the spread here is {below} that value, a ratio of {fbRatio}, and the two are not comparable: the emulated camera has a readout noise of {noise}, the beam here is Gaussian where the source used a flat one on a device of {pubPix} pixels, and the traps are the product\'s own draw. The published figure is context and no range of the case is built on it. {okAll} of {ofAll} methods with checked ranges sit inside all of them.',
      es: 'El método de referencia {ref} alcanza una eficiencia de {refEff} y una desviación estándar relativa de {refSd} por ciento en el modelo ideal, mientras que el GS ponderado da {sd06} por ciento y Gerchberg-Saxton {sd04} por ciento. El lazo de cámara baja la dispersión medida de {fb0} por ciento a {fbN} por ciento en {steps} pasos. Kim et al. 2019 informan {pubFinal} por ciento tras {pubSteps} pasos adaptativos sobre {pubFoci} focos desordenados; la dispersión aquí queda {below} ese valor, una razón de {fbRatio}, y los dos no son comparables: la cámara emulada tiene un ruido de lectura de {noise}, el haz aquí es gaussiano donde la fuente usó uno plano sobre un dispositivo de {pubPix} píxeles, y las trampas son un sorteo propio del producto. La cifra publicada es contexto y ningún rango del caso se apoya en ella. {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos.',
    },
    vals: (v, f) => {
      const p = v.manifest.params;
      const L = loop(v);
      const t = 'traps' in p.target ? p.target.traps : [];
      let minSq = Infinity;
      for (let i = 0; i < t.length; i += 1)
        for (let j = i + 1; j < t.length; j += 1) minSq = Math.min(minSq, (t[i].x_um - t[j].x_um) ** 2 + (t[i].y_um - t[j].y_um) ** 2);
      const half = t.reduce((m, x) => Math.max(m, Math.abs(x.x_um), Math.abs(x.y_um)), 0);
      return {
        ...common(v, f),
        minSep: f.n(Number.isFinite(minSq) ? Math.sqrt(minSq) : undefined, { digits: 3 }),
        half: f.n(t.length ? half : undefined, { digits: 3 }),
        gainRms: f.n(p.feedback?.camera.gain_rms, { digits: 2 }),
        noise: f.n(p.feedback?.camera.noise_rms, { digits: 2 }),
        fbGain: f.n(p.feedback?.gain, { digits: 2 }),
        steps: f.n(L.steps, { decimals: 0 }),
        fb0: f.n(L.first, { digits: 3 }),
        fbN: f.n(L.last, { digits: 3 }),
        sd06: nfmt(f, metricOf(v, 'M06', 'rel_std_pct'), { digits: 3 }),
        sd04: nfmt(f, metricOf(v, 'M04', 'rel_std_pct'), { digits: 3 }),
        pubFinal: f.n(KIM_DISORDERED.finalPct, { digits: 3 }),
        pubSteps: f.n(KIM_DISORDERED.steps, { decimals: 0 }),
        pubFoci: f.n(KIM_DISORDERED.foci, { decimals: 0 }),
        pubPix: f.n(KIM_DISORDERED.pixels, { decimals: 0 }),
        fbRatio: f.n(L.last !== undefined ? L.last / KIM_DISORDERED.finalPct : undefined, { digits: 3 }),
        below: L.last !== undefined && L.last <= KIM_DISORDERED.finalPct ? (f.lang === 'es' ? 'por debajo de' : 'below') : f.lang === 'es' ? 'por encima de' : 'above',
      };
    },
    extra: (v, f) => {
      const L = loop(v);
      const cond = pick(KIM_DISORDERED.conditions, f.lang);
      return [
        { label: f.lang === 'es' ? 'Dispersión tras los pasos (porcentaje)' : 'Spread after the steps (percent)', published: `${f.n(KIM_DISORDERED.finalPct, { digits: 3 })} (${cond})`, range: null, here: nfmt(f, L.last, { digits: 3 }), reading: ratioText(f, L.last, KIM_DISORDERED.finalPct) },
      ];
    },
  },

  C12_calibration: {
    question: {
      en: 'Does the engine reproduce the published comparison of the analytic and Gerchberg-Saxton baselines on a square-array task?',
      es: '¿Reproduce el motor la comparación publicada de las líneas base analíticas y de Gerchberg-Saxton en una tarea de matriz cuadrada?',
    },
    setup: {
      en: 'The calibration case sets the same task as the published comparison: {n} equal traps on a square lattice, at {lat} um spacing, which is {fu} Fourier units of the focal plane. It runs {nm} methods of the ladder, including the four of the published table (superposition, random superposition, Gerchberg-Saxton and weighted GS), with the seed {seed}, a budget of {iters} iterations and the product\'s Gaussian input beam on an SLM of {npix} by {npix} pixels. Its expected ranges for the four published methods are anchored to the published ordering with a margin, and the others are measured.',
      es: 'El caso de calibración fija la misma tarea que la comparación publicada: {n} trampas iguales en una red cuadrada, a {lat} um de separación, que son {fu} unidades de Fourier del plano focal. Corre {nm} métodos de la escalera, entre ellos los cuatro de la tabla publicada (superposición, superposición aleatoria, Gerchberg-Saxton y GS ponderado), con la semilla {seed}, un presupuesto de {iters} iteraciones y el haz de entrada gaussiano del producto sobre un SLM de {npix} por {npix} píxeles. Sus rangos esperados para los cuatro métodos publicados están anclados al orden publicado con un margen, y los demás son medidos.',
    },
    result: {
      en: 'The ordering of uniformity {kept}: weighted GS ({u06}) is above Gerchberg-Saxton ({u04}), which is above random superposition ({u02}) and plain superposition ({u01}). The efficiencies of the two iterative methods are {e04} and {e06} against the published {p04} and {p06}, so they {effCmp} the published values; the published table is for a flat beam on {pubPix} by {pubPix} pixels and the case uses a Gaussian beam on {npix} by {npix}, which lowers the efficiency ceiling. For random superposition the published uniformity is {pu02} and here it is {u02}. {okAll} of {ofAll} methods with checked ranges sit inside all of them.',
      es: 'El orden de la uniformidad {kept}: el GS ponderado ({u06}) está sobre Gerchberg-Saxton ({u04}), que está sobre la superposición aleatoria ({u02}) y la superposición simple ({u01}). Las eficiencias de los dos métodos iterativos son {e04} y {e06} frente a los {p04} y {p06} publicados, de modo que {effCmp} los valores publicados; la tabla publicada es para un haz plano en {pubPix} por {pubPix} píxeles y el caso usa un haz gaussiano en {npix} por {npix}, lo que baja el techo de la eficiencia. Para la superposición aleatoria la uniformidad publicada es {pu02} y aquí es {u02}. {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos.',
    },
    vals: (v, f) => {
      const g = (id: string, k: Metric) => nfmt(f, metricOf(v, id, k), { decimals: 3 });
      const pub = (id: string, k: 'efficiency' | 'uniformity') => f.n(DILEONARDO_TABLE.find((r) => r.method === id)?.[k], { digits: 2 });
      const pubV = (id: string, k: 'efficiency' | 'uniformity') => DILEONARDO_TABLE.find((r) => r.method === id)?.[k] ?? 0;
      const mv = (id: string, k: Metric) => metricOf(v, id, k) ?? 0;
      const orderKept = mv('M06', 'uniformity') > mv('M04', 'uniformity') && mv('M04', 'uniformity') > mv('M02', 'uniformity') && mv('M02', 'uniformity') >= mv('M01', 'uniformity');
      const effBelow = mv('M04', 'efficiency') < pubV('M04', 'efficiency') && mv('M06', 'efficiency') < pubV('M06', 'efficiency');
      return {
        ...common(v, f),
        u01: g('M01', 'uniformity'),
        u02: g('M02', 'uniformity'),
        u04: g('M04', 'uniformity'),
        u06: g('M06', 'uniformity'),
        e04: g('M04', 'efficiency'),
        e06: g('M06', 'efficiency'),
        p04: pub('M04', 'efficiency'),
        p06: pub('M06', 'efficiency'),
        pu02: pub('M02', 'uniformity'),
        pubPix: f.n(DILEONARDO.pixels, { decimals: 0 }),
        kept: orderKept ? (f.lang === 'es' ? 'se conserva' : 'is kept') : f.lang === 'es' ? 'NO se conserva' : 'is NOT kept',
        effCmp: effBelow ? (f.lang === 'es' ? 'quedan bajo' : 'fall below') : f.lang === 'es' ? 'no quedan bajo' : 'do not fall below',
      };
    },
    extra: (v, f) =>
      DILEONARDO_TABLE.flatMap((r) =>
        (['efficiency', 'uniformity'] as const).map((k) => {
          const here = metricOf(v, r.method, k);
          const lab = `${r.method} ${pick(r.name, f.lang)}: ${k === 'efficiency' ? (f.lang === 'es' ? 'eficiencia' : 'efficiency') : f.lang === 'es' ? 'uniformidad' : 'uniformity'}`;
          return {
            label: lab,
            published: `${f.n(r[k], { digits: 2 })} (${pick(DILEONARDO.conditions, f.lang)})`,
            range: null,
            here: nfmt(f, here, { decimals: 3 }),
            reading: here === undefined ? null : `${f.lang === 'es' ? 'diferencia' : 'difference'} ${signed(f, here - r[k], { decimals: 2 })}`,
          } as Row;
        }),
      ),
  },

  C04_disc_crosstalk: {
    question: {
      en: 'What does a uniform disc potential cost on a device with pixel crosstalk, and how much of it does a crosstalk-aware method recover?',
      es: '¿Qué cuesta un potencial de disco uniforme en un dispositivo con diafonía entre píxeles, y cuánto recupera un método que la modela?',
    },
    setup: {
      en: 'The target is a uniform disc of {radius} um radius, judged by the error of its signal region and not by trap metrics. The device has {bits} bits of phase and a pixel crosstalk kernel of width {sigma} pixels and exponent {q}, upsampled {up} times, and the optics are those of the atom setup ({wl} nm, {focal} mm, numerical aperture {na}). {nm} methods run with the seed {seed}; the point-trap methods do not apply to a shape, and the learned model of the ladder is not registered in this build.',
      es: 'El objetivo es un disco uniforme de {radius} um de radio, juzgado por el error de su región de señal y no por métricas de trampas. El dispositivo tiene {bits} bits de fase y un núcleo de diafonía entre píxeles de ancho {sigma} píxeles y exponente {q}, sobremuestreado {up} veces, y la óptica es la del montaje de átomos ({wl} nm, {focal} mm, apertura numérica {na}). Corren {nm} métodos con la semilla {seed}; los métodos de trampas puntuales no se aplican a una forma, y el modelo aprendido de la escalera no está registrado en esta versión.',
    },
    result: {
      en: 'The lowest signal error of the {nm} methods is {minErr} percent, reached by {minId} with an efficiency of {minEff}. The crosstalk-aware conjugate-gradient method M13 ends at {e13} percent against {e10} percent for the same optimizer without the crosstalk model, M10, so the model removes {gain} of the error at an efficiency of {eff13}. The published result is an error below {pub} percent with efficiency {pubLo} to {pubHi} percent, measured on their device: the error here is {ratio} times that bound, so {reproduced}, while M13 {bandVerb} the published efficiency band. A gap, when there is one, is a finding of this case and not a rounding of it.',
      es: 'El menor error de señal de los {nm} métodos es {minErr} por ciento, logrado por {minId} con una eficiencia de {minEff}. El método de gradiente conjugado con diafonía M13 termina en {e13} por ciento frente a {e10} por ciento del mismo optimizador sin el modelo de diafonía, M10, de modo que el modelo quita {gain} del error con una eficiencia de {eff13}. El resultado publicado es un error bajo {pub} por ciento con eficiencia de {pubLo} a {pubHi} por ciento, medido en su dispositivo: el error aquí es {ratio} veces esa cota, así que {reproduced}, mientras que M13 {bandVerb} la banda publicada de eficiencia. Una brecha, si la hay, es un hallazgo de este caso y no un redondeo.',
    },
    vals: (v, f) => {
      const t = v.manifest.params.target as { radius_um?: number };
      const d = v.manifest.params.device;
      const low = lowest(v, 'rel_std_pct');
      const e13 = metricOf(v, 'M13', 'rel_std_pct');
      const e10 = metricOf(v, 'M10', 'rel_std_pct');
      const eff13 = metricOf(v, 'M13', 'efficiency');
      const removed = e13 !== undefined && e10 !== undefined && e10 > 0 ? 1 - e13 / e10 : undefined;
      return {
        ...common(v, f),
        radius: f.n(t.radius_um, { digits: 3 }),
        bits: f.n(d?.bit_depth, { decimals: 0 }),
        sigma: f.n(d?.crosstalk?.sigma_per_px, { digits: 3 }),
        q: f.n(d?.crosstalk?.q, { digits: 3 }),
        up: f.n(d?.upsample, { decimals: 0 }),
        minErr: f.n(low?.value, { digits: 4 }),
        minId: low?.id ?? DASH,
        minEff: f.n(low ? metricOf(v, low.id, 'efficiency') : undefined, { decimals: 3 }),
        e13: nfmt(f, e13, { digits: 4 }),
        e10: nfmt(f, e10, { digits: 4 }),
        eff13: nfmt(f, eff13, { decimals: 3 }),
        gain: removed === undefined ? DASH : f.pct(removed * 100, { digits: 3 }),
        pub: f.n(SCHROFF_DISC.errorBelowPct, { digits: 2 }),
        pubLo: f.n(SCHROFF_DISC.effLowPct, { digits: 2 }),
        pubHi: f.n(SCHROFF_DISC.effHighPct, { digits: 2 }),
        ratio: f.n(low ? low.value / SCHROFF_DISC.errorBelowPct : undefined, { digits: 3 }),
        reproduced: low && low.value < SCHROFF_DISC.errorBelowPct ? (f.lang === 'es' ? 'la exactitud publicada es reproducida por al menos un método de esta versión' : 'the published accuracy is reproduced by at least one method of this build') : f.lang === 'es' ? 'la exactitud publicada NO es reproducida por ningún método de esta versión' : 'the published accuracy is NOT reproduced by any method of this build',
        bandVerb: eff13 !== undefined && eff13 * 100 >= SCHROFF_DISC.effLowPct && eff13 * 100 <= SCHROFF_DISC.effHighPct ? (f.lang === 'es' ? 'sí cae en' : 'does lie in') : f.lang === 'es' ? 'no cae en' : 'does not lie in',
      };
    },
    extra: (v, f) => {
      const low = lowest(v, 'rel_std_pct');
      const cond = pick(SCHROFF_DISC.conditions, f.lang);
      const e13 = metricOf(v, 'M13', 'efficiency');
      return [
        { label: f.lang === 'es' ? `Error de señal mínimo (porcentaje, ${low?.id ?? DASH})` : `Lowest signal error (percent, ${low?.id ?? DASH})`, published: `< ${f.n(SCHROFF_DISC.errorBelowPct, { digits: 2 })} (${cond})`, range: null, here: nfmt(f, low?.value, { digits: 4 }), reading: ratioText(f, low?.value, SCHROFF_DISC.errorBelowPct) },
        { label: f.lang === 'es' ? `Eficiencia de M13 (porcentaje)` : `Efficiency of M13 (percent)`, published: `${f.n(SCHROFF_DISC.effLowPct, { digits: 2 })} - ${f.n(SCHROFF_DISC.effHighPct, { digits: 2 })} (${cond})`, range: null, here: e13 === undefined ? DASH : f.n(e13 * 100, { digits: 3 }), reading: e13 === undefined ? null : e13 * 100 >= SCHROFF_DISC.effLowPct && e13 * 100 <= SCHROFF_DISC.effHighPct ? (f.lang === 'es' ? 'dentro de la banda publicada' : 'inside the published band') : f.lang === 'es' ? 'fuera de la banda publicada' : 'outside the published band' },
      ];
    },
  },

  C05_multiplane_vortices: {
    question: {
      en: 'Can traps at several depths, some of them optical vortices, be made equal from one hologram?',
      es: '¿Pueden hacerse iguales, desde un solo holograma, trampas a varias profundidades, algunas de ellas vórtices ópticos?',
    },
    setup: {
      en: 'The case holds {n} traps on {planes} planes spaced {dz} um apart, of which {nVort} are optical vortices of charge {charge}, with the optics of the bead setup: {wl} nm, a lens of {focal} mm, a nominal numerical aperture of {na} and an SLM of {npix} by {npix} pixels at {pitch} um pitch. The pupil defines a numerical aperture of {naPupil}, which puts the depth-of-field estimate, twice the wavelength over the square of that aperture, at {dof} um, so planes {dz} um apart are barely separable by any hologram; this is the stress of the case. {nm} methods run with the seed {seed}, and the reference method is {ref}.',
      es: 'El caso tiene {n} trampas en {planes} planos separados {dz} um entre sí, de las cuales {nVort} son vórtices ópticos de carga {charge}, con la óptica del montaje de esferas: {wl} nm, un lente de {focal} mm, una apertura numérica nominal de {na} y un SLM de {npix} por {npix} píxeles con paso de {pitch} um. La pupila define una apertura numérica de {naPupil}, que pone la estimación de la profundidad de campo, el doble de la longitud de onda sobre el cuadrado de esa apertura, en {dof} um, así que planos separados {dz} um son apenas separables por cualquier holograma; ésa es la tensión del caso. Corren {nm} métodos con la semilla {seed}, y el método de referencia es {ref}.',
    },
    result: {
      en: 'Direct search, the reference method {ref}, makes the traps equal to a relative standard deviation of {refSd} percent and a uniformity of {refU}, at an efficiency of {refEff}; weighted GS and the vortex rule reach {sdGs} percent at an efficiency of {effGs}, and the volumetric method M19 gives {sd19} percent. The published statement is that the traps are within {pub} percent after direct search; it does not say which spread statistic it uses, so the comparison is the relative standard deviation of {refSd} percent against {pub} percent and is only indicative. {validity}',
      es: 'La búsqueda directa, el método de referencia {ref}, iguala las trampas con una desviación estándar relativa de {refSd} por ciento y una uniformidad de {refU}, con una eficiencia de {refEff}; el GS ponderado y la regla de vórtices llegan a {sdGs} por ciento con una eficiencia de {effGs}, y el método volumétrico M19 da {sd19} por ciento. El enunciado publicado es que las trampas quedan dentro de {pub} por ciento tras la búsqueda directa; no dice qué estadístico de dispersión usa, así que la comparación es la desviación estándar relativa de {refSd} por ciento contra {pub} por ciento y es solo indicativa. {validity}',
    },
    vals: (v, f) => {
      const pl = planesUm(v.manifest);
      const dz = pl.length > 1 ? pl[1] - pl[0] : undefined;
      const geo = pupilDepthOfField(v.manifest);
      return {
        ...common(v, f),
        planes: f.n(pl.length, { decimals: 0 }),
        ...vortices(v, f),
        validity: validity(v, f),
        dz: f.n(dz, { digits: 3 }),
        naPupil: f.n(geo.naPupil, { digits: 3 }),
        dof: f.n(geo.dofUm, { digits: 3 }),
        sdGs: nfmt(f, metricOf(v, 'M06', 'rel_std_pct'), { digits: 3 }),
        effGs: nfmt(f, metricOf(v, 'M06', 'efficiency'), { decimals: 3 }),
        sd19: nfmt(f, metricOf(v, 'M19', 'rel_std_pct'), { digits: 3 }),
        pub: f.n(POLIN_ARRAY.withinPct, { decimals: 0 }),
      };
    },
    extra: (v, f) => {
      const r = refOf(v.manifest);
      return [
        { label: f.lang === 'es' ? `Dispersión relativa de las trampas (porcentaje, ${v.manifest.params.reference_method})` : `Relative spread of the traps (percent, ${v.manifest.params.reference_method})`, published: `${f.n(POLIN_ARRAY.withinPct, { decimals: 0 })} (${pick(POLIN_ARRAY.conditions, f.lang)})`, range: null, here: nfmt(f, r?.rel_std_pct, { digits: 3 }), reading: ratioText(f, r?.rel_std_pct, POLIN_ARRAY.withinPct) },
      ];
    },
  },

  C06_vortex_ring_line: {
    question: {
      en: 'Can extended structures, a ring of vortices, and point-like ones, a line of plain traps, be balanced in one hologram?',
      es: '¿Pueden equilibrarse en un solo holograma estructuras extendidas, un anillo de vórtices, y puntuales, una línea de trampas simples?',
    },
    setup: {
      en: 'The target mixes a ring of {nVort} vortex traps of charge {charge} with a line of {nPlain} plain traps of equal power, {n} traps in all, with the optics of the bead setup ({wl} nm, {focal} mm, nominal numerical aperture {na}, an SLM of {npix} by {npix} pixels). The ring traps are only a few focal bins apart, so the dark centre of each charged trap must stay resolved. {nm} methods run with the seed {seed}, and the reference method is {ref}. No published band exists for this mix, so the case is computed only.',
      es: 'El objetivo mezcla un anillo de {nVort} trampas de vórtice de carga {charge} con una línea de {nPlain} trampas simples de igual potencia, {n} trampas en total, con la óptica del montaje de esferas ({wl} nm, {focal} mm, apertura numérica nominal {na}, un SLM de {npix} por {npix} píxeles). Las trampas del anillo están separadas solo unos pocos bins focales, de modo que el centro oscuro de cada trampa cargada debe seguir resuelto. Corren {nm} métodos con la semilla {seed}, y el método de referencia es {ref}. No existe una banda publicada para esta mezcla, así que el caso es solo calculado.',
    },
    result: {
      en: 'The reference method {ref} equalises the {n} traps to a relative standard deviation of {refSd} percent and a uniformity of {refU}, at an efficiency of {refEff}. Weighted GS with the vortex rule gives {sdGs} percent, so the weighting balances the charged traps against the plain ones by construction, and direct search gives {sd09} percent at a lower efficiency of {eff09}. The bake names {best} as the most uniform method, and {okAll} of {ofAll} methods with checked ranges sit inside all of them. Because the case has no anchor, these numbers are a computed reference for the product and are compared with no published value. {validity}',
      es: 'El método de referencia {ref} iguala las {n} trampas con una desviación estándar relativa de {refSd} por ciento y una uniformidad de {refU}, con una eficiencia de {refEff}. El GS ponderado con la regla de vórtices da {sdGs} por ciento, de modo que la ponderación equilibra por construcción las trampas cargadas con las simples, y la búsqueda directa da {sd09} por ciento con una eficiencia menor de {eff09}. La generación nombra a {best} como el método más uniforme, y {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos. Como el caso no tiene ancla, estos números son una referencia calculada del producto y no se comparan con ningún valor publicado. {validity}',
    },
    vals: (v, f) => ({
      ...common(v, f),
      ...vortices(v, f),
      validity: validity(v, f),
      sdGs: nfmt(f, metricOf(v, 'M15', 'rel_std_pct'), { digits: 3 }),
      sd09: nfmt(f, metricOf(v, 'M09', 'rel_std_pct'), { digits: 3 }),
      eff09: nfmt(f, metricOf(v, 'M09', 'efficiency'), { decimals: 3 }),
    }),
  },

  C07_high_na: {
    question: {
      en: 'What changes when the numerical aperture is high, and where does the scalar model stop being valid?',
      es: '¿Qué cambia cuando la apertura numérica es alta, y dónde deja de ser válido el modelo escalar?',
    },
    setup: {
      en: 'The case runs a square array of {n} traps with {lat} um spacing at a numerical aperture of {na} in water ({nimm}), with a beam of {wl} nm through a lens of {focal} mm, on an SLM of {npix} by {npix} pixels. It is the honesty case: the engine is scalar (Fraunhofer and angular spectrum), whereas the real focus at this aperture is vectorial, so the manifest carries the flag that says so. {nm} methods run with the seed {seed}, and the reference method is {ref}.',
      es: 'El caso corre una matriz cuadrada de {n} trampas con {lat} um de separación a una apertura numérica de {na} en agua ({nimm}), con un haz de {wl} nm a través de un lente de {focal} mm, sobre un SLM de {npix} por {npix} píxeles. Es el caso de la honestidad: el motor es escalar (Fraunhofer y espectro angular), mientras que el foco real a esta apertura es vectorial, de modo que el manifiesto lleva la bandera que lo dice. Corren {nm} métodos con la semilla {seed}, y el método de referencia es {ref}.',
    },
    result: {
      en: 'Inside the scalar model the case behaves like the other square arrays: the reference method {ref} reaches an efficiency of {refEff}, a uniformity of {refU} and a relative standard deviation of {refSd} percent, and the bake names {best} as the most uniform method. Those numbers describe the scalar hologram only. No vectorial lane exists in this build and the source paper gives no numeric threshold of scalar failure that was read, so the size of the error at this aperture is UNVERIFIED and is not estimated here; the flag of the manifest, shown beside the table, is the whole claim. {okAll} of {ofAll} methods with checked ranges sit inside all of them.',
      es: 'Dentro del modelo escalar el caso se comporta como las otras matrices cuadradas: el método de referencia {ref} alcanza una eficiencia de {refEff}, una uniformidad de {refU} y una desviación estándar relativa de {refSd} por ciento, y la generación nombra a {best} como el método más uniforme. Esos números describen solo el holograma escalar. En esta versión no existe un carril vectorial y el artículo fuente no da un umbral numérico de falla escalar que se haya leído, de modo que el tamaño del error a esta apertura está SIN VERIFICAR y no se estima aquí; la bandera del manifiesto, mostrada junto a la tabla, es toda la afirmación. {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos.',
    },
    vals: (v, f) => ({ ...common(v, f), nimm: f.n(v.manifest.params.setup.n_imm, { digits: 3 }) }),
  },

  C08_device_limited: {
    question: {
      en: 'What does a real device cost a trap array, and what does a device-aware method win back?',
      es: '¿Qué le cuesta un dispositivo real a una matriz de trampas, y qué recupera un método que lo conoce?',
    },
    setup: {
      en: 'The case makes {n} traps with {lat} um spacing on a small SLM of {npix} by {npix} pixels, with a beam of {wl} nm and a lens of {focal} mm. The device has {bits} bits of phase, a pixel crosstalk kernel of width {sigma} pixels and exponent {q}, a fill factor of {fill} and a phase flicker of {flicker} rad rms, all together. {nm} methods run with the seed {seed}; the reference method is the device-aware weighted GS, {ref}, which the others are read against.',
      es: 'El caso hace {n} trampas con {lat} um de separación en un SLM pequeño de {npix} por {npix} píxeles, con un haz de {wl} nm y un lente de {focal} mm. El dispositivo tiene {bits} bits de fase, un núcleo de diafonía de ancho {sigma} píxeles y exponente {q}, un factor de llenado de {fill} y un parpadeo de fase de {flicker} rad rms, todo junto. Corren {nm} métodos con la semilla {seed}; el método de referencia es el GS ponderado que conoce el dispositivo, {ref}, contra el cual se leen los demás.',
    },
    result: {
      en: 'The device-aware method {ref} reaches a relative standard deviation of {refSd} percent and a uniformity of {refU} at an efficiency of {refEff}, whereas the phase-fixed weighted GS M07, which does not know the device, ends at {sd07} percent, a uniformity of {u07} and an efficiency of {eff07}. The device-aware method {recovers}, with an efficiency of {refEff} against {eff07} for M07. Only the crosstalk parameters have a published source (Schroff et al. 2023); the phase quantisation, the fill factor and the flicker have none in this build and are computed only, so no published value is compared and the absolute numbers belong to the stated device and not to an instrument. {okAll} of {ofAll} methods with checked ranges sit inside all of them.',
      es: 'El método que conoce el dispositivo, {ref}, alcanza una desviación estándar relativa de {refSd} por ciento y una uniformidad de {refU} con una eficiencia de {refEff}, mientras que el GS ponderado de fase fija M07, que no conoce el dispositivo, termina en {sd07} por ciento, una uniformidad de {u07} y una eficiencia de {eff07}. El método que conoce el dispositivo {recovers}, con una eficiencia de {refEff} frente a {eff07} de M07. Solo los parámetros de diafonía tienen fuente publicada (Schroff et al. 2023); la cuantización de la fase, el factor de llenado y el parpadeo no la tienen en esta versión y son solo calculados, así que no se compara ningún valor publicado y los números absolutos pertenecen al dispositivo declarado y no a un instrumento. {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos.',
    },
    vals: (v, f) => {
      const d = v.manifest.params.device;
      const e07 = metricOf(v, 'M07', 'efficiency');
      return {
        ...common(v, f),
        bits: f.n(d?.bit_depth, { decimals: 0 }),
        sigma: f.n(d?.crosstalk?.sigma_per_px, { digits: 3 }),
        q: f.n(d?.crosstalk?.q, { digits: 3 }),
        fill: f.n(d?.fill_factor, { digits: 3 }),
        flicker: f.n(d?.flicker_rad, { digits: 2 }),
        sd07: nfmt(f, metricOf(v, 'M07', 'rel_std_pct'), { digits: 3 }),
        u07: nfmt(f, metricOf(v, 'M07', 'uniformity'), { decimals: 3 }),
        eff07: nfmt(f, e07, { decimals: 3 }),
        recovers: (refOf(v.manifest)?.uniformity ?? 0) > (metricOf(v, 'M07', 'uniformity') ?? 1) ? (f.lang === 'es' ? 'recupera uniformidad' : 'wins back uniformity') : f.lang === 'es' ? 'no recupera uniformidad' : 'does not win back uniformity',
      };
    },
  },

  C09_aberrated: {
    question: {
      en: 'What do wavefront aberrations cost an array, and does a Zernike correction recover it?',
      es: '¿Qué le cuestan las aberraciones del frente de onda a una matriz, y la corrige una corrección de Zernike?',
    },
    setup: {
      en: 'The case makes {n} traps with {lat} um spacing under a system wavefront of {nModes} Zernike modes whose root-sum-square is {rms} waves, with a beam of {wl} nm through a lens of {focal} mm on an SLM of {npix} by {npix} pixels. {nm} methods run with the seed {seed}. Most methods ignore the aberration; the sensorless modal correction {ref} is the reference method and searches the modes to cancel them, and the aberration-robust hologram B4 designs for them without measuring.',
      es: 'El caso hace {n} trampas con {lat} um de separación bajo un frente de onda del sistema de {nModes} modos de Zernike cuya raíz de la suma de cuadrados es {rms} ondas, con un haz de {wl} nm a través de un lente de {focal} mm sobre un SLM de {npix} por {npix} píxeles. Corren {nm} métodos con la semilla {seed}. La mayoría de los métodos ignora la aberración; la corrección modal sin sensor {ref} es el método de referencia y busca los modos para cancelarlos, y el holograma robusto a aberraciones B4 se diseña para ellos sin medirlos.',
    },
    result: {
      en: 'Without the correction, weighted GS M06 holds {eff06} of the power in the traps with a relative standard deviation of {sd06} percent; with it, {ref} holds {refEff} with {refSd} percent, so the corrected efficiency is {gain} times the uncorrected one. The published result is a wavefront of {pubBefore} falling to {pubAfter} waves rms with the trap depth up by about {pubDepth} percent; the aberration injected here is {rms} waves and the efficiency of an equal-trap array is proportional to its trap depth, so the gain of {gainPct} percent is the comparable figure and it is {cmpWord} than the published one, whose conditions differ. The artifact does not carry the recovered wavefront, so the residual after the correction is not compared. The aberration-robust hologram B4 holds {eff04} of the power.',
      es: 'Sin la corrección, el GS ponderado M06 retiene {eff06} de la potencia en las trampas con una desviación estándar relativa de {sd06} por ciento; con ella, {ref} retiene {refEff} con {refSd} por ciento, de modo que la eficiencia corregida es {gain} veces la sin corregir. El resultado publicado es un frente de onda de {pubBefore} que baja a {pubAfter} ondas rms con la profundidad de trampa mayor en cerca de {pubDepth} por ciento; la aberración inyectada aquí es de {rms} ondas y la eficiencia de una matriz de trampas iguales es proporcional a su profundidad, así que la ganancia de {gainPct} por ciento es la cifra comparable y es {cmpWord} que la publicada, cuyas condiciones difieren. El artefacto no lleva el frente de onda recuperado, así que el residuo tras la corrección no se compara. El holograma robusto a aberraciones B4 retiene {eff04} de la potencia.',
    },
    vals: (v, f) => {
      const ab = v.manifest.params.aberration;
      const e06 = metricOf(v, 'M06', 'efficiency');
      const eRef = refOf(v.manifest)?.efficiency;
      const g = e06 && eRef !== undefined ? eRef / e06 : undefined;
      return {
        ...common(v, f),
        nModes: f.n(ab ? Object.keys(ab.noll).length : 0, { decimals: 0 }),
        rms: f.n(aberrationRmsWaves(v.manifest), { digits: 3 }),
        eff06: nfmt(f, e06, { decimals: 3 }),
        sd06: nfmt(f, metricOf(v, 'M06', 'rel_std_pct'), { digits: 3 }),
        eff04: nfmt(f, metricOf(v, 'B4', 'efficiency'), { decimals: 3 }),
        gain: f.n(g, { digits: 3 }),
        gainPct: g === undefined ? DASH : f.n((g - 1) * 100, { digits: 3 }),
        cmpWord: g !== undefined && (g - 1) * 100 > NOGRETTE_ABERRATION.depthGainPct ? (f.lang === 'es' ? 'mayor' : 'larger') : f.lang === 'es' ? 'menor o igual' : 'smaller or equal',
        pubBefore: f.n(NOGRETTE_ABERRATION.beforeWaves, { digits: 2 }),
        pubAfter: f.n(NOGRETTE_ABERRATION.afterWaves, { digits: 2 }),
        pubDepth: f.n(NOGRETTE_ABERRATION.depthGainPct, { decimals: 0 }),
      };
    },
    extra: (v, f) => {
      const e06 = metricOf(v, 'M06', 'efficiency');
      const eRef = refOf(v.manifest)?.efficiency;
      const g = e06 && eRef !== undefined ? (eRef / e06 - 1) * 100 : undefined;
      const rms = aberrationRmsWaves(v.manifest);
      const cond = pick(NOGRETTE_ABERRATION.conditions, f.lang);
      return [
        { label: f.lang === 'es' ? 'Frente de onda antes de corregir (ondas rms)' : 'Wavefront before correction (waves rms)', published: `${f.n(NOGRETTE_ABERRATION.beforeWaves, { digits: 2 })} (${cond})`, range: null, here: nfmt(f, rms ?? undefined, { digits: 3 }), reading: ratioText(f, rms ?? undefined, NOGRETTE_ABERRATION.beforeWaves) },
        { label: f.lang === 'es' ? 'Aumento de la profundidad de trampa (porcentaje; aquí, de la eficiencia)' : 'Increase of the trap depth (percent; here, of the efficiency)', published: `${f.n(NOGRETTE_ABERRATION.depthGainPct, { decimals: 0 })} (${cond})`, range: null, here: nfmt(f, g, { digits: 3 }), reading: ratioText(f, g, NOGRETTE_ABERRATION.depthGainPct) },
      ];
    },
  },

  C10_rearrangement: {
    question: {
      en: 'Can the atoms of a randomly loaded array be moved into a defect-free pattern without crossings, and does every moving trap stay lit?',
      es: '¿Pueden llevarse los átomos de una matriz cargada al azar a un patrón sin defectos y sin cruces, y sigue encendida cada trampa en movimiento?',
    },
    setup: {
      en: 'The array has {n} sites loaded with a probability of {loading}; at the case seed {loaded} sites hold an atom, and the target is a block of {target} sites. A Hungarian assignment with the cost distance to the power {alpha} pairs atoms with target sites, each move takes {perMove} steps, and the hologram of every one of the {frames} frames of the sequence is made by the registered method with a phase warm start from the previous frame. {nm} methods run with the seed {seed}; the reference method is the sorting method {ref}, whose trap metrics over all the sites are not a result, because it lights the target sites only.',
      es: 'La matriz tiene {n} sitios cargados con una probabilidad de {loading}; con la semilla del caso {loaded} sitios tienen un átomo, y el objetivo es un bloque de {target} sitios. Una asignación húngara con el costo distancia elevada a {alpha} empareja átomos con sitios objetivo, cada movimiento toma {perMove} pasos, y el holograma de cada uno de los {frames} cuadros de la secuencia lo hace el método registrado con un arranque de fase del cuadro anterior. Corren {nm} métodos con la semilla {seed}; el método de referencia es el método de ordenamiento {ref}, cuyas métricas de trampas sobre todos los sitios no son un resultado, porque ilumina solo los sitios objetivo.',
    },
    result: {
      en: 'The filling of the target rises from {fill0} to {fillN} over the {frames} frames, and the lowest intensity a moving trap reaches relative to the mean is {minT} (a value of one is a trap as bright as the average, a value near zero a trap that went dark). The sorting method {ref} has an efficiency of {refEff}, and the uniform methods M06, M07 and B2 give {sd06}, {sd07} and {sd02} percent of relative spread on the frames they make. The anchors (Barredo et al. 2016, Endres et al. 2016, Lee et al. 2017) describe the sorting scheme, not a numeric result the bake can be set against, so no published number is compared. The frame interval of {dt} s is an assumed value of the driver, not a measurement of a device.',
      es: 'El llenado del objetivo sube de {fill0} a {fillN} a lo largo de los {frames} cuadros, y la menor intensidad que alcanza una trampa en movimiento respecto del promedio es {minT} (un valor de uno es una trampa tan brillante como el promedio, un valor cercano a cero una trampa que se apagó). El método de ordenamiento {ref} tiene una eficiencia de {refEff}, y los métodos uniformes M06, M07 y B2 dan {sd06}, {sd07} y {sd02} por ciento de dispersión relativa en los cuadros que hacen. Las anclas (Barredo et al. 2016, Endres et al. 2016, Lee et al. 2017) describen el esquema de ordenamiento, no un resultado numérico contra el que se pueda fijar la generación, así que no se compara ningún número publicado. El intervalo entre cuadros de {dt} s es un valor supuesto del controlador, no la medición de un dispositivo.',
    },
    vals: (v, f) => {
      const r = v.manifest.params.rearrangement;
      const fr = v.trace.rearrangement;
      const first = fr?.frames[0];
      const loaded = first ? first.occupied.length + first.moving.length : undefined;
      const frames = fr?.frames ?? [];
      const dt = frames.length > 1 ? frames[1].t_s - frames[0].t_s : undefined;
      return {
        ...common(v, f),
        loading: f.n(r?.loading_p, { digits: 2 }),
        loaded: f.n(loaded, { decimals: 0 }),
        target: f.n(r?.target_ids.length, { decimals: 0 }),
        alpha: f.n(r?.alpha, { digits: 2 }),
        perMove: f.n(r?.steps_per_move, { decimals: 0 }),
        frames: f.n(frames.length, { decimals: 0 }),
        fill0: f.n(fr?.filling[0], { decimals: 3 }),
        fillN: f.n(fr?.filling[fr.filling.length - 1], { decimals: 3 }),
        minT: f.n(fr?.min_transient, { decimals: 3 }),
        sd06: nfmt(f, metricOf(v, 'M06', 'rel_std_pct'), { digits: 3 }),
        sd07: nfmt(f, metricOf(v, 'M07', 'rel_std_pct'), { digits: 3 }),
        sd02: nfmt(f, metricOf(v, 'B2', 'rel_std_pct'), { digits: 3 }),
        dt: f.n(dt, { digits: 3 }),
      };
    },
  },
};

/** The generic rows of every case: the ranges the bake checked for the reference method and for the case metrics, against what was measured. */
export function bakeRows(v: CaseView, f: Fmt): Row[] {
  const m = v.manifest;
  const rows: Row[] = [];
  const ref = m.params.reference_method;
  const r = refOf(m);
  const es = f.lang === 'es';
  const shaped = isShaped(m);
  const verdict = (x: number | undefined, rg: [number, number] | null): string | null =>
    x === undefined || rg === null ? null : inside(x, rg) ? (es ? 'dentro' : 'inside') : es ? 'fuera' : 'outside';
  const rangeText = (rg: [number, number] | null, o: { digits?: number; decimals?: number }) => (rg === null ? null : `${f.n(rg[0], o)} - ${f.n(rg[1], o)}`);
  if (r) {
    const defs: [Metric, string, string, { digits?: number; decimals?: number }][] = shaped
      ? [
          ['efficiency', `Eficiencia de ${ref}`, `Efficiency of ${ref}`, { decimals: 3 }],
          ['rel_std_pct', `Error de señal de ${ref} (porcentaje)`, `Signal error of ${ref} (percent)`, { digits: 3 }],
        ]
      : [
          ['efficiency', `Eficiencia de ${ref}`, `Efficiency of ${ref}`, { decimals: 3 }],
          ['uniformity', `Uniformidad de ${ref}`, `Uniformity of ${ref}`, { decimals: 3 }],
          ['rel_std_pct', `Desviación estándar relativa de ${ref} (porcentaje)`, `Relative standard deviation of ${ref} (percent)`, { digits: 3 }],
        ];
    for (const [k, lab_es, lab_en, o] of defs) {
      const rg = rangeOf(m, ref, k);
      if (!rg) continue;
      rows.push({ label: es ? lab_es : lab_en, published: null, range: rangeText(rg, o), here: f.n(r[k], o), reading: verdict(r[k], rg) });
    }
  }
  const L = loop(v);
  const caseRange = (key: string): [number, number] | null => {
    const x = m.expect[key];
    return x && x.length === 2 ? [x[0], x[1]] : null;
  };
  if (v.trace.feedback) {
    const a = caseRange('feedback_initial_rel_std_pct');
    const b = caseRange('feedback_final_rel_std_pct');
    if (a) rows.push({ label: es ? 'Dispersión medida antes del lazo (porcentaje)' : 'Measured spread before the loop (percent)', published: null, range: rangeText(a, { digits: 3 }), here: nfmt(f, L.first, { digits: 3 }), reading: verdict(L.first, a) });
    if (b) rows.push({ label: es ? 'Dispersión medida tras el lazo (porcentaje)' : 'Measured spread after the loop (percent)', published: null, range: rangeText(b, { digits: 3 }), here: nfmt(f, L.last, { digits: 3 }), reading: verdict(L.last, b) });
  }
  const o = particleOracle(v);
  const fc = caseRange('fc_ratio');
  if (o && fc) rows.push({ label: es ? 'Frecuencia ajustada sobre esperada' : 'Fitted over expected frequency', published: null, range: rangeText(fc, { digits: 3 }), here: f.n(o.ratio, { digits: 3 }), reading: verdict(o.ratio, fc) });
  const fr = v.trace.rearrangement;
  const ff = caseRange('final_filling');
  const mt = caseRange('min_transient');
  if (fr && ff) rows.push({ label: es ? 'Llenado final del objetivo' : 'Final filling of the target', published: null, range: rangeText(ff, { digits: 3 }), here: f.n(fr.filling[fr.filling.length - 1], { decimals: 3 }), reading: verdict(fr.filling[fr.filling.length - 1], ff) });
  if (fr && mt) rows.push({ label: es ? 'Menor intensidad transitoria de una trampa móvil' : 'Lowest transient intensity of a moving trap', published: null, range: rangeText(mt, { digits: 3 }), here: f.n(fr.min_transient, { decimals: 3 }), reading: verdict(fr.min_transient, mt) });
  return rows;
}
