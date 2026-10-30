// The beyond-the-state-of-the-art claims (area `comparison`), each with the measurement that supports it or the measured negative.
// Two kinds of evidence sit side by side and are labelled apart: what this page computes from the benchmark document at run time (the matrix
// cells that hold the challenger and its baseline) and what the SDD records from the acceptance test of the claim (the quantity the matrix
// does not score: five seeds on the crosstalk device, the transient intensity of a moving trap, an aberration ensemble, pointing errors).
// The verdict of each claim is computed from the numbers by the thresholds of the ladder row, never typed.
import { Cite, DocSection, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import type { BenchmarkResults, CaseManifest } from '../../lib/contract.types';
import { P } from '../bi';
import { LADDER } from '../methodology/ladder';
import { budgetText, CRITERIA, bs5Cells, median, ratioCells, skippedIn, verdictOf, type Lang, type Verdict, type RatioCell } from './data';
import { verdictLine } from './pareto';
import { RECORDED } from './recorded';
import { defaultBudget, Note, Ready, TableWrap, useBench, useNum, WRAP } from './shared';
import { WARM, type WarmRecord } from './warm';

const VERDICT_TEXT: Record<Verdict, { en: string; es: string }> = {
  supported: { en: 'supported', es: 'sustentada' },
  partly: { en: 'supported in a narrowed scope', es: 'sustentada en un alcance acotado' },
  'not-supported': { en: 'not supported', es: 'no sustentada' },
  'no-data': { en: 'no data', es: 'sin datos' },
};

/** The cells at the budget the claim is judged at: 30 iterations when the document has it, else every cell of the first iteration budget, else all. */
function headline(cells: RatioCell[], res: BenchmarkResults): RatioCell[] {
  const b = defaultBudget(res);
  const at = b ? cells.filter((c) => c.budget.kind === b.kind && c.budget.value === b.value) : cells;
  return at.length ? at : cells;
}

interface Summary {
  cells: RatioCell[];
  medFactor: number | null;
  minFactor: number | null;
  maxFactor: number | null;
  medRatio: number | null;
  passing: number;
  verdict: Verdict;
}
function summarise(cells: RatioCell[], res: BenchmarkResults, test: { sigmaFactor: number; effRatio: number }): Summary {
  const at = headline(cells, res);
  const f = at.map((c) => c.sigmaFactor);
  return {
    cells: at,
    medFactor: median(f),
    minFactor: f.length ? Math.min(...f) : null,
    maxFactor: f.length ? Math.max(...f) : null,
    medRatio: median(at.map((c) => c.effRatio)),
    passing: at.filter((c) => c.sigmaFactor >= test.sigmaFactor && c.effRatio >= test.effRatio).length,
    verdict: verdictOf(at.map((c) => c.sigmaFactor >= test.sigmaFactor && c.effRatio >= test.effRatio)),
  };
}

const recorded = (row: string) => RECORDED[row].numbers;

/** The ratio of M07 over B1 in the C08 manifest (the full device: 4-bit phase, crosstalk, fill factor and flicker), when the manifest holds both. */
function c08Ratio(m: CaseManifest | undefined): { factor: number; ratio: number } | null {
  const b1 = m?.methods.B1;
  const m07 = m?.methods.M07;
  if (!b1 || !m07 || !(b1.rel_std_pct > 0) || !(m07.efficiency > 0)) return null;
  return { factor: m07.rel_std_pct / b1.rel_std_pct, ratio: b1.efficiency / m07.efficiency };
}

function claimName(row: string, lang: Lang): string {
  return LADDER.find((r) => r.id === row)?.name[lang] ?? row;
}

function Block({ id, children }: { id: string; children: React.ReactNode }) {
  const lang = useShellLang() as Lang;
  return (
    <div data-claim={id} style={{ margin: '1rem 0' }}>
      <h3>
        {id} {claimName(id, lang)}
      </h3>
      {children}
    </div>
  );
}

function Bs3Table({ rec }: { rec: WarmRecord }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n } = useNum();
  const c = rec.control_without_the_network?.median_and_q3_iterations;
  const rows: [string, number | undefined][] = [
    [es ? 'Arranque aleatorio de M07, fijación de fase a la iteración 12 (la configuración de M07)' : 'M07 random start, phase fixed at iteration 12 (M07 as configured)', c?.random_nfix12?.[0]],
    [es ? 'Control sin red: arranque aleatorio, fijación de fase a la iteración 3' : 'Control without the network: random start, phase fixed at iteration 3', c?.random_nfix3?.[0]],
    [es ? 'Arranque aprendido, fijación de fase a la iteración 3' : 'Learned start, phase fixed at iteration 3', c?.model_nfix3?.[0]],
  ];
  return (
    <TableWrap>
      <table className="caos-table" data-state="ready" data-table="bs3">
        <caption>
          {es
            ? `BS-3 sobre ${rec.metrics.held_out_n} geometrías reservadas: mediana de iteraciones hasta 1 por ciento de desviación estándar relativa (presupuesto de ${rec.iteration_budget} iteraciones). El control usa una de cada dos geometrías reservadas generadas.`
            : `BS-3 on ${rec.metrics.held_out_n} held-out geometries: median iterations to 1 percent relative standard deviation (budget of ${rec.iteration_budget} iterations). The control uses every second generated held-out geometry.`}
        </caption>
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Arranque' : 'Start'}</th>
            <th>{es ? 'Mediana de iteraciones' : 'Median iterations'}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="caos-col-text">{es ? 'Arranque aleatorio de M07 (la comparación del criterio)' : 'M07 random start (the criterion comparison)'}</td>
            <td>{n(rec.metrics.iterations_to_1pct.random.median)}</td>
          </tr>
          <tr>
            <td className="caos-col-text">{es ? 'Arranque aprendido (la comparación del criterio)' : 'Learned start (the criterion comparison)'}</td>
            <td>{n(rec.metrics.iterations_to_1pct.model.median)}</td>
          </tr>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{k}</td>
              <td>{n(v)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

function ClaimsBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { data } = useBench();
  const { n, d } = useNum();
  const rec1 = recorded('BS-1');
  const rec2 = recorded('BS-2');
  const rec4 = recorded('BS-4');
  const budget = defaultBudget(res);
  const s1 = useMemo(() => summarise(ratioCells(res, 'B1', 'M07', 'device'), res, CRITERIA.bs1), [res]);
  const s4 = useMemo(() => summarise(ratioCells(res, 'B4', 'M07', 'device'), res, CRITERIA.bs4), [res]);
  const s4ideal = useMemo(() => summarise(ratioCells(res, 'B4', 'M07', 'ideal'), res, CRITERIA.bs4), [res]);
  const b5 = budget ? bs5Cells(res, budget) : [];
  const v5 = verdictOf(b5.map((c) => c.hvFront >= c.hvClassical));
  const c08 = c08Ratio(data.c08.state === 'ready' ? data.c08.data : undefined);
  const b3skipped = skippedIn(res).filter((s) => s.method === 'B3');
  const b2rows = res.rows.filter((r) => r.method === 'B2').length;
  const b4aber = rec4.medianFactor >= CRITERIA.bs4.sigmaFactor && rec4.efficiencyRatio >= CRITERIA.bs4.effRatio;
  const b1rec = rec1.medianFactor >= CRITERIA.bs1.sigmaFactor && rec1.efficiencyRatio >= CRITERIA.bs1.effRatio;
  // BS-2: the acceptance task, the long lattice moves and C10 at 137 frames meet the threshold; C10 at equal frames does not (LPI leads)
  const b2cells = [rec2.b2Low >= rec2.threshold, rec2.longMedianA >= rec2.threshold, rec2.longMedianB >= rec2.threshold, rec2.c10LpiLeadsAtEqualFrames === 0];
  const v2 = verdictOf(b2cells);
  const warm = WARM;
  const ratio3 = warm ? warm.metrics.iterations_to_1pct.random.median / warm.metrics.iterations_to_1pct.model.median : null;
  const v3: Verdict = ratio3 === null ? 'no-data' : ratio3 >= CRITERIA.bs3.iterationFactor ? 'supported' : 'not-supported';
  const v1: Verdict = s1.cells.length ? s1.verdict : b1rec ? 'supported' : 'not-supported';
  const v4: Verdict = b4aber ? 'partly' : 'not-supported';

  const sdd = (row: string) => (es ? `la fila ${row} del SDD` : `row ${row} of the SDD`);
  const summaryRows: { id: string; baseline: string; matrix: string; recorded: string; verdict: Verdict; test: string }[] = [
    {
      id: 'BS-1',
      baseline: es ? 'M07 (igual al WGS-Kim de slmsuite)' : 'M07 (equal to slmsuite WGS-Kim)',
      matrix: s1.cells.length
        ? es
          ? `factor de mediana ${n(s1.medFactor)} (${n(s1.minFactor)} a ${n(s1.maxFactor)}) en ${s1.cells.length} geometrías, razón de eficiencia ${n(s1.medRatio)}; ${s1.passing} cumplen ambos umbrales`
          : `median factor ${n(s1.medFactor)} (${n(s1.minFactor)} to ${n(s1.maxFactor)}) over ${s1.cells.length} geometries, efficiency ratio ${n(s1.medRatio)}; ${s1.passing} meet both thresholds`
        : es ? 'sin celdas con B1 y M07 sobre el dispositivo en este documento' : 'no cell with B1 and M07 on the device in this document',
      recorded: es
        ? `mediana ${n(rec1.medianFactor)} veces (${n(rec1.lowFactor)} a ${n(rec1.highFactor)} en ${rec1.seeds} semillas) con ${n(rec1.efficiencyRatio)} de la eficiencia; ${n(rec1.fullDeviceFactor)} veces en el dispositivo C08 completo`
        : `median ${n(rec1.medianFactor)} times (${n(rec1.lowFactor)} to ${n(rec1.highFactor)} over ${rec1.seeds} seeds) at ${n(rec1.efficiencyRatio)} of the efficiency; ${n(rec1.fullDeviceFactor)} times on the full C08 device`,
      verdict: v1,
      test: RECORDED['BS-1'].test,
    },
    {
      id: 'BS-2',
      baseline: es ? 'Interpolación lineal de fase (M16)' : 'Linear phase interpolation (M16)',
      matrix: es ? `no se mide en la matriz: sus celdas puntúan cada cuadro de forma estática (${b2rows} filas de B2), no la intensidad transitoria` : `not measured by the matrix: its cells score each frame statically (${b2rows} B2 rows), not the transient intensity`,
      recorded: es
        ? `B2 ${n(rec2.b2Low)} a ${n(rec2.b2High)} contra ${n(rec2.lpiLow)} a ${n(rec2.lpiHigh)} de LPI, con paso máximo ${n(rec2.stepLimit)} unidades de Fourier; con ${rec2.c10EqualFrames} cuadros en C10, LPI lidera en toda semilla`
        : `B2 ${n(rec2.b2Low)} to ${n(rec2.b2High)} against ${n(rec2.lpiLow)} to ${n(rec2.lpiHigh)} for LPI, at a peak step of at most ${n(rec2.stepLimit)} Fourier units; at ${rec2.c10EqualFrames} frames on C10, LPI leads in every seed`,
      verdict: v2,
      test: RECORDED['BS-2'].test,
    },
    {
      id: 'BS-3',
      baseline: es ? 'Arranque aleatorio de M07' : 'M07 random start',
      matrix: b3skipped.length ? (es ? `${b3skipped.length} ${b3skipped.length === 1 ? 'celda de B3 no corrida' : 'celdas de B3 no corridas'}: ${b3skipped[0].reason.es}` : `${b3skipped.length} B3 ${b3skipped.length === 1 ? 'cell' : 'cells'} not run: ${b3skipped[0].reason.en}`) : es ? 'sin celdas de B3 listadas como no corridas' : 'no B3 cell listed as not run',
      recorded: warm
        ? es
          ? `mediana de ${n(warm.metrics.iterations_to_1pct.model.median)} iteraciones contra ${n(warm.metrics.iterations_to_1pct.random.median)} del arranque aleatorio (${n(ratio3)} veces, el criterio pide ${CRITERIA.bs3.iterationFactor}); el control sin red gana lo mismo`
          : `median ${n(warm.metrics.iterations_to_1pct.model.median)} iterations against ${n(warm.metrics.iterations_to_1pct.random.median)} from the random start (${n(ratio3)} times, the criterion asks for ${CRITERIA.bs3.iterationFactor}); the control without the network gains as much`
        : es ? 'el registro del modelo rechazado no está en esta generación' : 'the record of the rejected model is not in this build',
      verdict: v3,
      test: 'tests/learned/test_b3_warm_start.py',
    },
    {
      id: 'BS-4',
      baseline: es ? 'M07' : 'M07',
      matrix: s4.cells.length
        ? es
          ? `sin aberración en la matriz; contra el dispositivo C08, factor de mediana ${n(s4.medFactor)} y razón de eficiencia ${n(s4.medRatio)} en ${s4.cells.length} geometrías (en el ideal, ${n(s4ideal.medFactor)})`
          : `no aberration in the matrix; on the C08 device, median factor ${n(s4.medFactor)} and efficiency ratio ${n(s4.medRatio)} over ${s4.cells.length} geometries (on the ideal device ${n(s4ideal.medFactor)})`
        : es ? 'sin celdas con B4 y M07 en este documento' : 'no cell with B4 and M07 in this document',
      recorded: es
        ? `aberraciones: mediana ${n(rec4.medianFactor)} veces (${n(rec4.lowFactor)} a ${n(rec4.highFactor)} en ${rec4.seeds} semillas, ${rec4.ensemble} muestras) con ${n(rec4.efficiencyRatio)} de la eficiencia; errores de puntería: ${n(rec4.pointingFactor)} veces`
        : `aberrations: median ${n(rec4.medianFactor)} times (${n(rec4.lowFactor)} to ${n(rec4.highFactor)} over ${rec4.seeds} seeds, ${rec4.ensemble} samples) at ${n(rec4.efficiencyRatio)} of the efficiency; pointing errors: ${n(rec4.pointingFactor)} times`,
      verdict: v4,
      test: RECORDED['BS-4'].test,
    },
    {
      id: 'BS-5',
      baseline: es ? 'M04, M05, M06 y M09 (sus puntos)' : 'M04, M05, M06 and M09 (their points)',
      matrix: b5.length
        ? es
          ? `${b5.filter((c) => c.hvFront >= c.hvClassical).length} de ${b5.length} geometrías con frente tienen un hipervolumen del frente mayor o igual`
          : `${b5.filter((c) => c.hvFront >= c.hvClassical).length} of ${b5.length} geometries with a front have a front hypervolume at least as large`
        : es ? 'el documento no trae un frente de B5' : 'the document holds no B5 front',
      recorded: es ? 'se calcula íntegra desde el documento (pestaña de frentes de Pareto)' : 'computed entirely from the document (the Pareto fronts tab)',
      verdict: v5,
      test: 'tests/methods/beyond/test_b5_pareto.py',
    },
  ];

  return (
    <>
      <TableWrap>
        <table className="caos-table" data-state="ready" data-table="claims">
          <caption>
            {es
              ? `Las cinco afirmaciones del nivel más allá contra su línea base más fuerte. La columna de la matriz se calcula al cargar la página desde el documento de resultados, con ${budget ? budgetText(budget).es : 'el presupuesto por defecto'} y los parámetros por defecto en ambos lados; la columna del registro es lo que el SDD guarda de la prueba de aceptación de la afirmación, y una prueba lo mantiene igual a esa fila. El veredicto aplica el umbral de la fila de la escalera a esas cifras.`
              : `The five claims of the beyond tier against their strongest baseline. The matrix column is computed when the page loads, from the results document, at ${budget ? budgetText(budget).en : 'the default budget'} and with default parameters on both sides; the recorded column is what the SDD keeps from the acceptance test of the claim, and a test holds it equal to that row. The verdict applies the threshold of the ladder row to those figures.`}
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Afirmación' : 'Claim'}</th>
              <th className="caos-col-text">{es ? 'Línea base' : 'Baseline'}</th>
              <th className="caos-col-text">{es ? 'En esta matriz (leído del documento)' : 'In this matrix (read from the document)'}</th>
              <th className="caos-col-text">{es ? 'Prueba de aceptación (registrado en el SDD)' : 'Acceptance test (recorded in the SDD)'}</th>
              <th className="caos-col-text">{es ? 'Veredicto' : 'Verdict'}</th>
            </tr>
          </thead>
          <tbody>
            {summaryRows.map((r) => (
              <tr key={r.id} data-claim-row={r.id} data-verdict={r.verdict}>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                  {r.id} {claimName(r.id, lang)}
                </td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{r.baseline}</td>
                <td className="caos-col-text" style={{ ...WRAP, whiteSpace: 'normal' }}>{r.matrix}</td>
                <td className="caos-col-text" style={{ ...WRAP, whiteSpace: 'normal' }}>{r.recorded}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}><strong>{VERDICT_TEXT[r.verdict][lang]}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <Block id="BS-1">
        <P
          en={
            <>
              BS-1 keeps the weights of the weighted GS and replaces its phase update by gradient steps through the crosstalk kernel and the quantizer, so the hologram is optimised for the device that will display it <Cite id="schroff2023" />. The claim is a relative standard deviation at least {CRITERIA.bs1.sigmaFactor} times below M07 on the crosstalk device with an efficiency at most {d((1 - CRITERIA.bs1.effRatio) * 100, 0)} percent lower, against the M07 that equals slmsuite&apos;s WGS-Kim <Cite id="kim2019" />. In this matrix {s1.cells.length ? <>the median factor is {n(s1.medFactor)} over {s1.cells.length} geometries at {budget ? budgetText(budget).en : 'the default budget'}, from {n(s1.minFactor)} to {n(s1.maxFactor)}, and {s1.passing} of them meet both thresholds</> : <>there is no cell that holds both methods on the device</>}. {c08 ? <>On the full C08 device of the case manifest, with 4-bit phase and flicker, the factor is {n(c08.factor)} at an efficiency ratio of {n(c08.ratio)}, read from the baked case.</> : null} The acceptance test, over {rec1.seeds} seeds on the crosstalk device, records a median of {n(rec1.medianFactor)} ({n(rec1.lowFactor)} to {n(rec1.highFactor)}) at {n(rec1.efficiencyRatio)} of the efficiency, and {n(rec1.fullDeviceFactor)} times on the full device: the claim holds, and its size depends on how much of the device the model covers.
            </>
          }
          es={
            <>
              BS-1 conserva los pesos del GS ponderado y reemplaza su actualización de fase por pasos de gradiente a través del núcleo de diafonía y del cuantizador, de modo que el holograma se optimiza para el dispositivo que lo mostrará <Cite id="schroff2023" />. La afirmación es una desviación estándar relativa al menos {CRITERIA.bs1.sigmaFactor} veces menor que la de M07 en el dispositivo con diafonía, con una eficiencia a lo más {d((1 - CRITERIA.bs1.effRatio) * 100, 0)} por ciento menor, contra el M07 que es igual al WGS-Kim de slmsuite <Cite id="kim2019" />. En esta matriz {s1.cells.length ? <>el factor de mediana es {n(s1.medFactor)} en {s1.cells.length} geometrías con {budget ? budgetText(budget).es : 'el presupuesto por defecto'}, de {n(s1.minFactor)} a {n(s1.maxFactor)}, y {s1.passing} de ellas cumplen ambos umbrales</> : <>no hay una celda que tenga ambos métodos sobre el dispositivo</>}. {c08 ? <>En el dispositivo C08 completo del manifiesto del caso, con fase de 4 bits y parpadeo, el factor es {n(c08.factor)} con una razón de eficiencia de {n(c08.ratio)}, leído del caso generado.</> : null} La prueba de aceptación, sobre {rec1.seeds} semillas en el dispositivo con diafonía, registra una mediana de {n(rec1.medianFactor)} ({n(rec1.lowFactor)} a {n(rec1.highFactor)}) con {n(rec1.efficiencyRatio)} de la eficiencia, y {n(rec1.fullDeviceFactor)} veces en el dispositivo completo: la afirmación se cumple, y su tamaño depende de cuánto del dispositivo cubre el modelo.
            </>
          }
        />
        <Slice cells={s1.cells} />
      </Block>

      <Block id="BS-2">
        <P
          en={
            <>
              BS-2 optimises each intermediate hologram of a rearrangement with the trap phases locked to a smooth trajectory, where linear phase interpolation does not optimise its intermediate frames <Cite id="lpi2025" />. Its quantity is the minimum transient intensity of a moving trap over its mean, which the matrix does not score (its cells hold the static metrics of a frame, and the {b2rows} rows of B2 in this document are those). The acceptance test records {n(rec2.b2Low)} to {n(rec2.b2High)} for B2 against {n(rec2.lpiLow)} to {n(rec2.lpiHigh)} for linear phase interpolation, which meets the {n(rec2.threshold)} threshold while the peak step per frame is at most {n(rec2.stepLimit)} Fourier units, and on long lattice moves a median of {n(rec2.longMedianA)} and {n(rec2.longMedianB)}, with {rec2.longSeedsMet} of {rec2.longSeeds} seeds. The measured limit is as stated: on the long sort of C10 at {rec2.c10EqualFrames} frames linear phase interpolation leads in every seed, and B2 needs the end phases and {rec2.c10Frames} frames to reach {n(rec2.c10B2Low)} to {n(rec2.c10B2High)} on {rec2.c10SeedsMet} of {rec2.c10Seeds} seeds of M16's plan (median {n(rec2.c10B2Median)}, against {n(rec2.c10LpiLow)} to {n(rec2.c10LpiHigh)} for linear phase interpolation), with one seed collapsing on its phase path. The claim is therefore supported in the short-step regime and not in general.
            </>
          }
          es={
            <>
              BS-2 optimiza cada holograma intermedio de un reordenamiento con las fases de las trampas ligadas a una trayectoria suave, donde la interpolación lineal de fase no optimiza sus cuadros intermedios <Cite id="lpi2025" />. Su cantidad es la intensidad transitoria mínima de una trampa en movimiento sobre su media, que la matriz no puntúa (sus celdas guardan las métricas estáticas de un cuadro, y las {b2rows} filas de B2 de este documento son esas). La prueba de aceptación registra {n(rec2.b2Low)} a {n(rec2.b2High)} para B2 contra {n(rec2.lpiLow)} a {n(rec2.lpiHigh)} de la interpolación lineal de fase, que cumple el umbral de {n(rec2.threshold)} mientras el paso máximo por cuadro sea a lo más {n(rec2.stepLimit)} unidades de Fourier, y en movimientos largos de la red una mediana de {n(rec2.longMedianA)} y {n(rec2.longMedianB)}, con {rec2.longSeedsMet} de {rec2.longSeeds} semillas. El límite medido es el que se declara: en la clasificación larga de C10 con {rec2.c10EqualFrames} cuadros la interpolación lineal de fase lidera en toda semilla, y B2 necesita las fases finales y {rec2.c10Frames} cuadros para llegar a {n(rec2.c10B2Low)} a {n(rec2.c10B2High)} en {rec2.c10SeedsMet} de {rec2.c10Seeds} semillas del plan de M16 (mediana {n(rec2.c10B2Median)}, contra {n(rec2.c10LpiLow)} a {n(rec2.c10LpiHigh)} de la interpolación lineal de fase), con una semilla que colapsa en su trayectoria de fase. La afirmación queda entonces sustentada en el régimen de pasos cortos y no en general.
            </>
          }
        />
      </Block>

      <Block id="BS-3">
        <P
          en={
            <>
              BS-3 asked a permutation-invariant network over the trap coordinates for the initial trap phases of the phase-fixed WGS, expecting at least {CRITERIA.bs3.iterationFactor} times fewer iterations to 1 percent than a random start. It is reported as refuted. {warm ? <>On {warm.metrics.held_out_n} held-out geometries the network start needs a median of {n(warm.metrics.iterations_to_1pct.model.median)} iterations against {n(warm.metrics.iterations_to_1pct.random.median)} from the random start, a factor of {n(ratio3)}, below the {CRITERIA.bs3.iterationFactor} claimed; the gain appears only with the phase fixed early, and a control with the same early fix and no network gains as much (table below). The model is not released: the readiness document marks the slot as answered by its baseline, the random start of M07, and the benchmark lists the B3 cells as not run.</> : <>The record of the rejected model is not in this build, so the measured values cannot be shown here.</>}
            </>
          }
          es={
            <>
              BS-3 le pidió a una red invariante a permutaciones sobre las coordenadas de las trampas las fases iniciales del WGS de fase fija, esperando al menos {CRITERIA.bs3.iterationFactor} veces menos iteraciones hasta 1 por ciento que un arranque aleatorio. Se informa como refutada. {warm ? <>Sobre {warm.metrics.held_out_n} geometrías reservadas el arranque de la red necesita una mediana de {n(warm.metrics.iterations_to_1pct.model.median)} iteraciones contra {n(warm.metrics.iterations_to_1pct.random.median)} del arranque aleatorio, un factor de {n(ratio3)}, bajo el {CRITERIA.bs3.iterationFactor} afirmado; la ganancia aparece solo con la fase fijada temprano, y un control con la misma fijación temprana y sin red gana lo mismo (tabla siguiente). El modelo no se publica: el documento de disponibilidad marca el espacio como atendido por su línea base, el arranque aleatorio de M07, y el benchmark lista las celdas de B3 como no corridas.</> : <>El registro del modelo rechazado no está en esta generación, de modo que los valores medidos no pueden mostrarse aquí.</>}
            </>
          }
        />
        <Note ids={['warmstart-model']} />
        {warm ? <Bs3Table rec={warm} /> : null}
      </Block>

      <Block id="BS-4">
        <P
          en={
            <>
              BS-4 minimises the expected cost over residual aberrations instead of correcting one, because the published corrections are global or per site and never robust <Cite id="machu2025" />. The claim is a 95th percentile of the relative standard deviation at least {n(CRITERIA.bs4.sigmaFactor)} times below M07 over an ensemble of aberrations, at an efficiency at most {d((1 - CRITERIA.bs4.effRatio) * 100, 0)} percent lower. The acceptance test records a median of {n(rec4.medianFactor)} ({n(rec4.lowFactor)} to {n(rec4.highFactor)} over {rec4.seeds} seeds, {rec4.ensemble} samples) at {n(rec4.efficiencyRatio)} of the efficiency, so the aberration claim holds. The same test measures robustness to pointing errors and finds {n(rec4.pointingFactor)} times, below the {n(CRITERIA.bs4.sigmaFactor)} threshold: the spot width bounds what a hologram can do about a pointing error, the claim does not extend to it, and it is reported as a measured negative and not claimed. {s4.cells.length ? <>The matrix applies no aberration, so its cells are not the claim; they show that on the C08 device B4 stands at a median factor of {n(s4.medFactor)} and an efficiency ratio of {n(s4.medRatio)} against M07, and at {n(s4ideal.medFactor)} on the ideal device.</> : null}
            </>
          }
          es={
            <>
              BS-4 minimiza el costo esperado sobre aberraciones residuales en lugar de corregir una, porque las correcciones publicadas son globales o por sitio y nunca robustas <Cite id="machu2025" />. La afirmación es un percentil 95 de la desviación estándar relativa al menos {n(CRITERIA.bs4.sigmaFactor)} veces menor que el de M07 sobre un conjunto de aberraciones, con una eficiencia a lo más {d((1 - CRITERIA.bs4.effRatio) * 100, 0)} por ciento menor. La prueba de aceptación registra una mediana de {n(rec4.medianFactor)} ({n(rec4.lowFactor)} a {n(rec4.highFactor)} en {rec4.seeds} semillas, {rec4.ensemble} muestras) con {n(rec4.efficiencyRatio)} de la eficiencia, de modo que la afirmación de aberraciones se cumple. La misma prueba mide la robustez a errores de puntería y encuentra {n(rec4.pointingFactor)} veces, bajo el umbral de {n(CRITERIA.bs4.sigmaFactor)}: el ancho de la mancha acota lo que un holograma puede hacer frente a un error de puntería, la afirmación no se extiende a él, y se informa como un negativo medido y no se afirma. {s4.cells.length ? <>La matriz no aplica aberración, así que sus celdas no son la afirmación; muestran que en el dispositivo C08 B4 está en un factor de mediana de {n(s4.medFactor)} y una razón de eficiencia de {n(s4.medRatio)} frente a M07, y en {n(s4ideal.medFactor)} en el dispositivo ideal.</> : null}
            </>
          }
        />
      </Block>

      <Block id="BS-5">
        <P
          en={
            <>
              BS-5 asks for the whole efficiency-uniformity front instead of one trade-off point <Cite id="dileonardo2007" />, and its criterion is a hypervolume at least that of the union of the M04, M05, M06 and M09 points. {b5.length ? <>{verdictLine(v5, false)} The areas, the front and the dominated points are on the Pareto fronts tab; here the count is {b5.filter((c) => c.hvFront >= c.hvClassical).length} of {b5.length} geometries with a front, at {budget ? budgetText(budget).en : 'the default budget'}. The margin of the ladder row is small by design, so it is worth reading the areas and not only the verdict.</> : <>The document holds no front, so the claim has no measurement on this page.</>}
            </>
          }
          es={
            <>
              BS-5 pide el frente completo de eficiencia-uniformidad en lugar de un punto de intercambio <Cite id="dileonardo2007" />, y su criterio es un hipervolumen al menos igual al de la unión de los puntos de M04, M05, M06 y M09. {b5.length ? <>{verdictLine(v5, true)} Las áreas, el frente y los puntos dominados están en la pestaña de frentes de Pareto; aquí el conteo es {b5.filter((c) => c.hvFront >= c.hvClassical).length} de {b5.length} geometrías con frente, con {budget ? budgetText(budget).es : 'el presupuesto por defecto'}. El margen de la fila de la escalera es pequeño por diseño, así que conviene leer las áreas y no solo el veredicto.</> : <>El documento no trae un frente, así que la afirmación no tiene una medición en esta página.</>}
            </>
          }
        />
      </Block>
      <p className="caos-plot-note" lang={lang}>
        {es ? `Fuentes de lo registrado: ${sdd('BS-1')}, ${sdd('BS-2')} y ${sdd('BS-4')} del SDD, medidas por ${[RECORDED['BS-1'].test, RECORDED['BS-2'].test, RECORDED['BS-4'].test].join(', ')}.` : `Sources of what is recorded: ${sdd('BS-1')}, ${sdd('BS-2')} and ${sdd('BS-4')}, measured by ${[RECORDED['BS-1'].test, RECORDED['BS-2'].test, RECORDED['BS-4'].test].join(', ')}.`}
      </p>
    </>
  );
}

/** The cells behind a factor: one row per geometry at the headline budget, so the median is never the only number the reader has. */
function Slice({ cells }: { cells: RatioCell[] }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const { n } = useNum();
  if (!cells.length) return null;
  return (
    <TableWrap>
      <table className="caos-table" data-state="ready" data-table="bs1-cells">
        <caption>
          {es ? 'BS-1: B1 frente a M07 sobre el dispositivo C08, una fila por geometría y presupuesto del titular, ambos con parámetros por defecto.' : 'BS-1: B1 against M07 on the C08 device, one row per geometry at the headline budget, both with default parameters.'}
        </caption>
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
            <th className="caos-col-text">{es ? 'Presupuesto' : 'Budget'}</th>
            <th>{es ? 'Factor de uniformidad' : 'Uniformity factor'}</th>
            <th>{es ? 'Razón de eficiencia' : 'Efficiency ratio'}</th>
            <th>{es ? 'Semillas' : 'Seeds'}</th>
            <th className="caos-col-text">{es ? 'Umbrales' : 'Thresholds'}</th>
          </tr>
        </thead>
        <tbody>
          {cells.map((c) => (
            <tr key={`${c.geometry}-${c.budget.kind}-${c.budget.value}`}>
              <td className="caos-col-text">{c.geometry}</td>
              <td className="caos-col-text">{budgetText(c.budget)[lang]}</td>
              <td>{n(c.sigmaFactor)}</td>
              <td>{n(c.effRatio)}</td>
              <td>{c.seeds}</td>
              <td className="caos-col-text">{c.sigmaFactor >= CRITERIA.bs1.sigmaFactor && c.effRatio >= CRITERIA.bs1.effRatio ? (es ? 'cumple ambos' : 'meets both') : es ? 'no cumple' : 'not met'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function ClaimsTopic() {
  const { data } = useBench();
  return (
    <DocSection
      title={{ en: 'Beyond the state of the art: each claim with its measurement', es: 'Más allá del estado del arte: cada afirmación con su medición' }}
      id="claims"
      area="comparison"
      refs={['schroff2023', 'kim2019', 'lpi2025', 'machu2025', 'dileonardo2007']}
    >
      <P
        en="Each beyond-the-state-of-the-art method is DinHot's own proposal, grounded in a sourced gap and judged by a threshold written before the measurement. The page does not defend them: it shows for each claim the figure the matrix gives, the figure of the acceptance test where the matrix cannot reproduce the quantity, the threshold, and the verdict that results. A claim that the measurement does not support is stated as not supported, and a claim that holds only in part is stated with the part."
        es="Cada método del nivel más allá del estado del arte es una propuesta propia de DinHot, fundada en un vacío documentado y juzgada por un umbral escrito antes de la medición. La página no los defiende: muestra para cada afirmación la cifra que da la matriz, la cifra de la prueba de aceptación donde la matriz no puede reproducir la cantidad, el umbral y el veredicto que resulta. Una afirmación que la medición no sustenta se declara no sustentada, y una que se cumple solo en parte se declara con esa parte."
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <ClaimsBody res={res} />}</Ready>
    </DocSection>
  );
}

