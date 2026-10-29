// The method ladder of the SDD ("Method ladder", docs/design/SDD.md) as data, so that every method of the Methodology page is named once, in
// its tier, with its design record (docs/design/methods/<file>). The ids, tiers and names are the SDD's rows; a vitest in this folder reads the
// SDD and fails when the two disagree. The Methodology page shows the table of each tier and of each topic from this one list.
import { useShellLang } from '@fasl-work/caos-app-shell';

export type Tier = 'classical' | 'sota' | 'beyond';

export interface LadderRow {
  id: string;
  tier: Tier;
  /** The engine id of a beyond method (B1 to B5), else the same as `id`. */
  engine: string;
  name: { en: string; es: string };
  /** The file of the design record in docs/design/methods/. */
  record: string;
}

/** The blob root of the design records on the repository (the default branch). */
export const RECORDS_URL = 'https://github.com/fsantibanezleal/CEFOP_DinHot/blob/main/docs/design/methods/';

export const LADDER: LadderRow[] = [
  { id: 'M01', tier: 'classical', engine: 'M01', name: { en: 'Superposition of prisms and lenses', es: 'Superposición de prismas y lentes' }, record: 'M01-superposition.md' },
  { id: 'M02', tier: 'classical', engine: 'M02', name: { en: 'Random superposition', es: 'Superposición aleatoria' }, record: 'M02-random-superposition.md' },
  { id: 'M03', tier: 'classical', engine: 'M03', name: { en: 'Random mask', es: 'Máscara aleatoria' }, record: 'M03-random-mask.md' },
  { id: 'M04', tier: 'classical', engine: 'M04', name: { en: 'Gerchberg-Saxton, point-trap and FFT forms', es: 'Gerchberg-Saxton, formas de trampas puntuales y FFT' }, record: 'M04-gerchberg-saxton.md' },
  { id: 'M05', tier: 'classical', engine: 'M05', name: { en: 'Generalized adaptive additive', es: 'Aditivo adaptativo generalizado' }, record: 'M05-gaa.md' },
  { id: 'M06', tier: 'classical', engine: 'M06', name: { en: 'Weighted GS', es: 'GS ponderado' }, record: 'M06-gsw.md' },
  { id: 'M09', tier: 'classical', engine: 'M09', name: { en: 'Direct search', es: 'Búsqueda directa' }, record: 'M09-direct-search.md' },
  { id: 'M14', tier: 'classical', engine: 'M14', name: { en: 'Zernike correction and sensorless modal recovery', es: 'Corrección de Zernike y recuperación modal sin sensor' }, record: 'M14-zernike-correction.md' },
  { id: 'M15', tier: 'classical', engine: 'M15', name: { en: 'Laguerre-Gaussian vortex traps', es: 'Trampas de vórtice de Laguerre-Gauss' }, record: 'M15-vortex-traps.md' },
  { id: 'M19', tier: 'classical', engine: 'M19', name: { en: 'Multi-plane GS', es: 'GS multiplano (GS 3D volumétrico de Whyte y Courtial)' }, record: 'M19-volumetric-3d-gs.md' },
  { id: 'M07', tier: 'sota', engine: 'M07', name: { en: 'Phase-fixed weighted GS', es: 'GS ponderado de fase fija' }, record: 'M07-phase-fixed-wgs.md' },
  { id: 'M08', tier: 'sota', engine: 'M08', name: { en: 'MRAF', es: 'MRAF' }, record: 'M08-mraf.md' },
  { id: 'M10', tier: 'sota', engine: 'M10', name: { en: 'Conjugate-gradient minimization', es: 'Minimización por gradiente conjugado' }, record: 'M10-conjugate-gradient.md' },
  { id: 'M11', tier: 'sota', engine: 'M11', name: { en: 'Wirtinger gradient descent with Adam', es: 'Descenso de gradiente de Wirtinger con Adam' }, record: 'M11-wirtinger-adam.md' },
  { id: 'M12', tier: 'sota', engine: 'M12', name: { en: 'Closed-loop WGS on an emulated camera', es: 'WGS de lazo cerrado sobre una cámara emulada' }, record: 'M12-closed-loop-wgs.md' },
  { id: 'M13', tier: 'sota', engine: 'M13', name: { en: 'Device-aware CG with pixel crosstalk', es: 'CG consciente del dispositivo con diafonía de píxeles' }, record: 'M13-crosstalk-aware-cg.md' },
  { id: 'M16', tier: 'sota', engine: 'M16', name: { en: 'Hungarian assignment and linear phase interpolation', es: 'Asignación húngara e interpolación lineal de fase' }, record: 'M16-rearrangement.md' },
  { id: 'M17', tier: 'sota', engine: 'M17', name: { en: 'Multi-plane CNN hologram with an optional volumetric GS refinement (DeepCGH-style)', es: 'Holograma de CNN multiplano con un refinamiento opcional por el GS volumétrico (estilo DeepCGH)' }, record: 'M17-unsupervised-cnn-hologram.md' },
  { id: 'M18', tier: 'sota', engine: 'M18', name: { en: 'Optimal-transport initialized MRAF', es: 'MRAF inicializado por transporte óptimo' }, record: 'M18-ot-initialized-mraf.md' },
  { id: 'BS-1', tier: 'beyond', engine: 'B1', name: { en: 'Device-aware weighted GS', es: 'GS ponderado consciente del dispositivo' }, record: 'BS-1-device-aware-wgs.md' },
  { id: 'BS-2', tier: 'beyond', engine: 'B2', name: { en: 'Flicker-bounded phase-continuous sequence', es: 'Secuencia de fase continua acotada en parpadeo' }, record: 'BS-2-flicker-bounded-sequence.md' },
  { id: 'BS-3', tier: 'beyond', engine: 'B3', name: { en: 'Learned warm start for phase-fixed WGS (refuted)', es: 'Arranque aprendido para el WGS de fase fija (refutado)' }, record: 'BS-3-learned-warm-start.md' },
  { id: 'BS-4', tier: 'beyond', engine: 'B4', name: { en: 'Aberration-robust hologram', es: 'Holograma robusto a aberraciones' }, record: 'BS-4-aberration-robust-hologram.md' },
  { id: 'BS-5', tier: 'beyond', engine: 'B5', name: { en: 'Efficiency-uniformity Pareto front', es: 'Frente de Pareto eficiencia-uniformidad' }, record: 'BS-5-pareto-front.md' },
];

const TIER_NAME: Record<Tier, { en: string; es: string }> = {
  classical: { en: 'classical', es: 'clásico' },
  sota: { en: 'state of the art', es: 'estado del arte' },
  beyond: { en: 'beyond the state of the art', es: 'más allá del estado del arte' },
};

/** The rows of a list of ladder ids, in the order given; an id outside the ladder throws, so no method outside it can be shown. */
export function rowsOf(ids: string[]): LadderRow[] {
  return ids.map((id) => {
    const row = LADDER.find((r) => r.id === id);
    if (!row) throw new Error(`Methodology: ${id} is not a row of the method ladder`);
    return row;
  });
}

/** The table of ladder rows: id, tier, method and the link to its design record. */
export function MethodTable({ ids, tier }: { ids?: string[]; tier?: Tier }) {
  const es = useShellLang() === 'es';
  const rows = ids ? rowsOf(ids) : LADDER.filter((r) => r.tier === tier);
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Id de la escalera' : 'Ladder id'}</th>
            <th className="caos-col-text">{es ? 'Nivel' : 'Tier'}</th>
            <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
            <th className="caos-col-text">{es ? 'Registro de diseño' : 'Design record'}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} data-ladder-id={r.id}>
              <td className="caos-col-text" style={{ whiteSpace: 'nowrap' }}>
                {r.id}
                {r.engine !== r.id ? ` (${es ? 'motor' : 'engine'} ${r.engine})` : ''}
              </td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? TIER_NAME[r.tier].es : TIER_NAME[r.tier].en}</td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? r.name.es : r.name.en}</td>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                <a href={`${RECORDS_URL}${r.record}`} target="_blank" rel="noreferrer">
                  {r.record}
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
