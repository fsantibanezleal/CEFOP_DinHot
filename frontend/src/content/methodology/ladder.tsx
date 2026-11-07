// The method ladder of the SDD ("Method ladder", docs/design/SDD.md) as data, so that every method of the Methodology page is named once, in
// its group, with its design record (docs/design/methods/<file>). The ids, groups and names are the SDD's rows; a vitest in this folder reads the
// SDD and fails when the two disagree. The Methodology page shows the table of each topic from this one list.
import { useShellLang } from '@fasl-work/caos-app-shell';
import { ID } from '../../lib/methodIds';

export type Tier = 'classical' | 'sota' | 'beyond';

export interface LadderRow {
  id: string;
  tier: Tier;
  /** The engine id of a beyond method (B1 to B5), else the same as `id`. */
  engine: string;
  name: { en: string; es: string };
  /** The short name for a table cell or a chart tick. */
  short: { en: string; es: string };
  /** The design record's file name in docs/design/methods/ without its id prefix (`<id>-<slug>`). */
  slug: string;
}

/** The blob root of the design records on the repository (the default branch). */
export const RECORDS_URL = 'https://github.com/fsantibanezleal/CEFOP_DinHot/blob/main/docs/design/methods/';

export const LADDER: LadderRow[] = [
  { id: ID.M01, tier: 'classical', engine: ID.M01, name: { en: 'Superposition of prisms and lenses', es: 'Superposición de prismas y lentes' }, short: { en: 'Prisms and lenses', es: 'Prismas y lentes' }, slug: 'superposition.md' },
  { id: ID.M02, tier: 'classical', engine: ID.M02, name: { en: 'Random superposition', es: 'Superposición aleatoria' }, short: { en: 'Random superposition', es: 'Superposición aleatoria' }, slug: 'random-superposition.md' },
  { id: ID.M03, tier: 'classical', engine: ID.M03, name: { en: 'Random mask', es: 'Máscara aleatoria' }, short: { en: 'Random mask', es: 'Máscara aleatoria' }, slug: 'random-mask.md' },
  { id: ID.M04, tier: 'classical', engine: ID.M04, name: { en: 'Gerchberg-Saxton, point-trap and FFT forms', es: 'Gerchberg-Saxton, formas de trampas puntuales y FFT' }, short: { en: 'GS', es: 'GS' }, slug: 'gerchberg-saxton.md' },
  { id: ID.M05, tier: 'classical', engine: ID.M05, name: { en: 'Generalized adaptive additive', es: 'Aditivo adaptativo generalizado' }, short: { en: 'GAA', es: 'GAA' }, slug: 'gaa.md' },
  { id: ID.M06, tier: 'classical', engine: ID.M06, name: { en: 'Weighted GS', es: 'GS ponderado' }, short: { en: 'Weighted GS', es: 'GS ponderado' }, slug: 'gsw.md' },
  { id: ID.M09, tier: 'classical', engine: ID.M09, name: { en: 'Direct search', es: 'Búsqueda directa' }, short: { en: 'Direct search', es: 'Búsqueda directa' }, slug: 'direct-search.md' },
  { id: ID.M14, tier: 'classical', engine: ID.M14, name: { en: 'Zernike correction and sensorless modal recovery', es: 'Corrección de Zernike y recuperación modal sin sensor' }, short: { en: 'Zernike correction', es: 'Corrección de Zernike' }, slug: 'zernike-correction.md' },
  { id: ID.M15, tier: 'classical', engine: ID.M15, name: { en: 'Laguerre-Gaussian vortex traps', es: 'Trampas de vórtice de Laguerre-Gauss' }, short: { en: 'LG vortex', es: 'Vórtice LG' }, slug: 'vortex-traps.md' },
  { id: ID.M19, tier: 'classical', engine: ID.M19, name: { en: 'Multi-plane GS', es: 'GS multiplano (GS 3D volumétrico de Whyte y Courtial)' }, short: { en: 'Multi-plane GS', es: 'GS multiplano' }, slug: 'volumetric-3d-gs.md' },
  { id: ID.M07, tier: 'sota', engine: ID.M07, name: { en: 'Phase-fixed weighted GS', es: 'GS ponderado de fase fija' }, short: { en: 'Phase-fixed WGS', es: 'WGS de fase fija' }, slug: 'phase-fixed-wgs.md' },
  { id: ID.M08, tier: 'sota', engine: ID.M08, name: { en: 'MRAF', es: 'MRAF' }, short: { en: 'MRAF', es: 'MRAF' }, slug: 'mraf.md' },
  { id: ID.M10, tier: 'sota', engine: ID.M10, name: { en: 'Conjugate-gradient minimization', es: 'Minimización por gradiente conjugado' }, short: { en: 'Conjugate gradient', es: 'Gradiente conjugado' }, slug: 'conjugate-gradient.md' },
  { id: ID.M11, tier: 'sota', engine: ID.M11, name: { en: 'Wirtinger gradient descent with Adam', es: 'Descenso de gradiente de Wirtinger con Adam' }, short: { en: 'Wirtinger-Adam', es: 'Wirtinger-Adam' }, slug: 'wirtinger-adam.md' },
  { id: ID.M12, tier: 'sota', engine: ID.M12, name: { en: 'Closed-loop WGS on an emulated camera', es: 'WGS de lazo cerrado sobre una cámara emulada' }, short: { en: 'Closed-loop WGS', es: 'WGS de lazo cerrado' }, slug: 'closed-loop-wgs.md' },
  { id: ID.M13, tier: 'sota', engine: ID.M13, name: { en: 'Device-aware CG with pixel crosstalk', es: 'CG consciente del dispositivo con diafonía de píxeles' }, short: { en: 'Device-aware CG', es: 'CG consciente del dispositivo' }, slug: 'crosstalk-aware-cg.md' },
  { id: ID.M16, tier: 'sota', engine: ID.M16, name: { en: 'Hungarian assignment and linear phase interpolation', es: 'Asignación húngara e interpolación lineal de fase' }, short: { en: 'Hungarian and LPI', es: 'Húngaro e interpolación lineal' }, slug: 'rearrangement.md' },
  { id: ID.M17, tier: 'sota', engine: ID.M17, name: { en: 'Multi-plane CNN hologram with an optional volumetric GS refinement (DeepCGH-style)', es: 'Holograma de CNN multiplano con un refinamiento opcional por el GS volumétrico (estilo DeepCGH)' }, short: { en: 'Multi-plane CNN', es: 'CNN multiplano' }, slug: 'unsupervised-cnn-hologram.md' },
  { id: ID.M18, tier: 'sota', engine: ID.M18, name: { en: 'Optimal-transport initialized MRAF', es: 'MRAF inicializado por transporte óptimo' }, short: { en: 'OT-initialized MRAF', es: 'MRAF inicializado por transporte óptimo' }, slug: 'ot-initialized-mraf.md' },
  { id: ID.B1, tier: 'beyond', engine: ID.B1, name: { en: 'Device-aware weighted GS', es: 'GS ponderado consciente del dispositivo' }, short: { en: 'Device-aware WGS', es: 'WGS consciente del dispositivo' }, slug: 'device-aware-wgs.md' },
  { id: ID.B2, tier: 'beyond', engine: ID.B2, name: { en: 'Flicker-bounded phase-continuous sequence', es: 'Secuencia de fase continua acotada en parpadeo' }, short: { en: 'Flicker-bounded sequence', es: 'Secuencia acotada en parpadeo' }, slug: 'flicker-bounded-sequence.md' },
  { id: ID.B3, tier: 'beyond', engine: ID.B3, name: { en: 'Learned warm start for phase-fixed WGS (refuted)', es: 'Arranque aprendido para el WGS de fase fija (refutado)' }, short: { en: 'Learned warm start', es: 'Arranque aprendido' }, slug: 'learned-warm-start.md' },
  { id: ID.B4, tier: 'beyond', engine: ID.B4, name: { en: 'Aberration-robust hologram', es: 'Holograma robusto a aberraciones' }, short: { en: 'Aberration-robust hologram', es: 'Holograma robusto a aberraciones' }, slug: 'aberration-robust-hologram.md' },
  { id: ID.B5, tier: 'beyond', engine: ID.B5, name: { en: 'Efficiency-uniformity Pareto front', es: 'Frente de Pareto eficiencia-uniformidad' }, short: { en: 'Efficiency-uniformity front', es: 'Frente eficiencia-uniformidad' }, slug: 'pareto-front.md' },
];

/** What a reader sees: the 19 methods of the literature are published, the five of DinHot are proposed. */
export type Kind = 'published' | 'proposed';
export const KIND_NAME: Record<Kind, { en: string; es: string }> = {
  published: { en: 'published', es: 'publicado' },
  proposed: { en: 'proposed', es: 'propuesto' },
};
export const kindOfTier = (tier: Tier): Kind => (tier === 'beyond' ? 'proposed' : 'published');

/** The rows of a list of ladder ids, in the order given; an id outside the ladder throws, so no method outside it can be shown. */
export function rowsOf(ids: string[]): LadderRow[] {
  return ids.map((id) => {
    const row = LADDER.find((r) => r.id === id);
    if (!row) throw new Error(`Methodology: ${id} is not a row of the method ladder`);
    return row;
  });
}

/** The table of ladder rows: kind, method (by its name, never its id) and the link to its design record. */
export function MethodTable({ ids, tier }: { ids?: string[]; tier?: Tier }) {
  const es = useShellLang() === 'es';
  const rows = ids ? rowsOf(ids) : LADDER.filter((r) => r.tier === tier);
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Tipo' : 'Kind'}</th>
            <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
            <th className="caos-col-text">{es ? 'Registro de diseño' : 'Design record'}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} data-ladder-id={r.id}>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? KIND_NAME[kindOfTier(r.tier)].es : KIND_NAME[kindOfTier(r.tier)].en}</td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? r.name.es : r.name.en}</td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                <a href={`${RECORDS_URL}${r.id}-${r.slug}`} target="_blank" rel="noreferrer">
                  {es ? 'Abrir el registro' : 'Open the record'}
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
