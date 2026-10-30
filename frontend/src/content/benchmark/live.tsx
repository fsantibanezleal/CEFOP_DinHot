// The live panel (area `live`): the engine of the site measured in the reader's browser, on demand and never at rest. One method (M07 by
// default) runs on the default case of the index in the dedicated worker, one warm-up and several timed runs, and the panel reports the
// median wall-clock of a whole run (the method and the scoring from the final phase) against the budget the case's lane gate declares,
// which backend answered (the CPU path or WebGPU) and why, and the metrics of the last run. The benchmark matrix's own M07 time is shown
// beside it as what it is: another engine, another grid, another machine.
import { ChipGroup, DocSection, PlotCard, useShellLang } from '@fasl-work/caos-app-shell';
import { useCallback, useRef, useState } from 'react';
import { loadManifest } from '../../api/artifacts';
import type { BenchmarkResults, CaseManifest } from '../../lib/contract.types';
import { getEngine, type Engine } from '../../workbench/engine';
import { P } from '../bi';
import { median } from './data';
import { Note, Ready, TableWrap, useBench, useNum, WRAP } from './shared';

/** One warm-up and this many timed runs: the first run of a worker pays for its modules and its plans, so it is not timed into the median. */
const TIMED_RUNS = 4;
const METHODS = ['M04', 'M06', 'M07'];

interface Outcome {
  method: string;
  caseId: string;
  budgetMs: number;
  nPix: number;
  traps: number;
  iterations: number;
  runsMs: number[];
  backend: 'cpu' | 'gpu';
  fallbackReason: string | null;
  metrics: { efficiency: number; uniformity: number; relStdPct: number };
  timing: { methodMs: number; scoreMs: number; yieldMs: number };
}

type State = { phase: 'idle' } | { phase: 'running'; done: number } | { phase: 'done'; out: Outcome } | { phase: 'error'; message: string } | { phase: 'unavailable' };

function trapsOf(m: CaseManifest): number {
  const t = m.params.target;
  return t.kind === 'traps' ? t.traps.length : 0;
}

function LivePanel({ res }: { res: BenchmarkResults | null }) {
  const lang = useShellLang();
  const es = lang === 'es';
  const { data } = useBench();
  const { n, d } = useNum();
  const [method, setMethod] = useState('M07');
  const [backend, setBackend] = useState<'auto' | 'cpu'>('auto');
  const [state, setState] = useState<State>({ phase: 'idle' });
  const engineRef = useRef<Engine | null>(null);
  const token = useRef(0);

  const run = useCallback(async () => {
    const mine = ++token.current;
    setState({ phase: 'running', done: 0 });
    try {
      const index = data.index.state === 'ready' ? data.index.data : null;
      if (!index) throw new Error(es ? 'El índice de casos no está disponible.' : 'The case index is not available.');
      engineRef.current ??= await getEngine();
      const engine = engineRef.current;
      if (!engine.available) {
        setState({ phase: 'unavailable' });
        return;
      }
      const manifest = await loadManifest(index.default_case);
      const params = { case_id: manifest.case_id, ...manifest.params };
      const times: number[] = [];
      let last = null as Awaited<ReturnType<typeof engine.client.run>> | null;
      for (let i = 0; i < TIMED_RUNS + 1; i++) {
        if (token.current !== mine) return;
        const t0 = performance.now();
        last = await engine.client.run({ params, method, options: { iterations: manifest.params.budget.iterations, backend } });
        const wall = performance.now() - t0;
        if (i > 0) times.push(wall);
        setState({ phase: 'running', done: i + 1 });
      }
      if (token.current !== mine || !last) return;
      setState({
        phase: 'done',
        out: {
          method,
          caseId: manifest.case_id,
          budgetMs: manifest.gate.run_ms_budget,
          nPix: last.nPix,
          traps: trapsOf(manifest),
          iterations: manifest.params.budget.iterations ?? 0,
          runsMs: times,
          backend: last.backend,
          fallbackReason: last.fallbackReason,
          metrics: last.metrics,
          timing: last.timing,
        },
      });
    } catch (e) {
      if (token.current === mine) setState({ phase: 'error', message: e instanceof Error ? e.message : String(e) });
    }
  }, [backend, data.index, es, method]);

  const cancel = useCallback(() => {
    token.current++;
    engineRef.current?.client.cancel();
    setState({ phase: 'idle' });
  }, []);

  const running = state.phase === 'running';
  const matrixTime = res?.rows.find((r) => r.method === method && r.geometry === 'G1' && r.device === 'ideal' && r.budget_kind === 'iterations' && r.budget === 30 && r.params === 'default');
  return (
    <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem 1.5rem', margin: '0.5rem 0' }}>
        <ChipGroup
          id="live-method"
          label={{ en: 'Method', es: 'Método' }}
          options={METHODS.map((m) => ({ id: m, label: { en: m, es: m } }))}
          value={method}
          onChange={setMethod}
        />
        <ChipGroup
          id="live-backend"
          label={{ en: 'Backend', es: 'Motor de cálculo' }}
          options={[
            { id: 'auto', label: { en: 'Automatic (WebGPU if it agrees)', es: 'Automático (WebGPU si coincide)' } },
            { id: 'cpu', label: { en: 'CPU only', es: 'Solo CPU' } },
          ]}
          value={backend}
          onChange={(id) => setBackend(id as 'auto' | 'cpu')}
        />
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <button type="button" className="btn" disabled={running} onClick={() => void run()} data-action="run-live">
          {es ? `Medir ${method} en este navegador (1 calentamiento y ${TIMED_RUNS} corridas)` : `Time ${method} in this browser (1 warm-up and ${TIMED_RUNS} runs)`}
        </button>
        {running ? (
          <button type="button" className="btn" onClick={cancel}>
            {es ? 'Cancelar' : 'Cancel'}
          </button>
        ) : null}
        <span className="caos-plot-note" role="status" aria-live="polite">
          {state.phase === 'idle' ? (es ? 'Nada corre hasta que se pulsa el botón.' : 'Nothing runs until the button is pressed.') : null}
          {state.phase === 'running' ? (es ? `Corrida ${state.done} de ${TIMED_RUNS + 1}` : `Run ${state.done} of ${TIMED_RUNS + 1}`) : null}
        </span>
      </div>
      {state.phase === 'unavailable' ? (
        <p className="caos-pending" data-state="unavailable">
          {es ? 'El motor en vivo no está en esta versión del sitio; el panel no tiene nada que medir.' : 'The live engine is not on this build of the site; the panel has nothing to measure.'}
        </p>
      ) : null}
      {state.phase === 'error' ? (
        <p className="caos-pending" data-state="error" style={WRAP}>
          {state.message}
        </p>
      ) : null}
      {state.phase === 'done' ? (
        <Result out={state.out} matrixSeconds={matrixTime?.time_s.median ?? null} n={n} d={d} />
      ) : null}
    </>
  );
}

function Result({ out, matrixSeconds, n, d }: { out: Outcome; matrixSeconds: number | null; n: (v: number | null | undefined, digits?: number) => string; d: (v: number | null | undefined, decimals: number) => string }) {
  const es = useShellLang() === 'es';
  const med = median(out.runsMs) ?? 0;
  const inside = med <= out.budgetMs;
  const title = { en: 'Wall-clock of each timed run against the lane budget', es: 'Reloj de cada corrida cronometrada contra el presupuesto del carril' };
  return (
    <>
      <PlotCard title={title} lane="live" provenance="synthetic">
        <TableWrap>
          <table className="caos-table" data-state="ready" data-table="live-timing">
            <caption>
              {es
                ? `${out.method} en el caso ${out.caseId} (${out.traps} trampas, grilla de ${out.nPix} por ${out.nPix}, ${out.iterations} iteraciones), en este navegador: el reloj de una corrida completa, con la puntuación desde la fase final.`
                : `${out.method} on the case ${out.caseId} (${out.traps} traps, a ${out.nPix} by ${out.nPix} grid, ${out.iterations} iterations), in this browser: the wall-clock of a whole run, with the scoring from the final phase.`}
            </caption>
            <thead>
              <tr>
                <th className="caos-col-text">{es ? 'Medida' : 'Measure'}</th>
                <th>{es ? 'Valor' : 'Value'}</th>
                <th className="caos-col-text">{es ? 'Lectura' : 'Reading'}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="caos-col-text">{es ? 'Mediana de las corridas (ms)' : 'Median of the runs (ms)'}</td>
                <td>{d(med, 0)}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                  {out.runsMs.map((t) => d(t, 0)).join(', ')} ms
                </td>
              </tr>
              <tr>
                <td className="caos-col-text">{es ? 'Presupuesto del carril en vivo (ms)' : 'Live lane budget (ms)'}</td>
                <td>{d(out.budgetMs, 0)}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }} data-inside={inside}>
                  {inside ? (es ? 'dentro del presupuesto en esta máquina' : 'inside the budget on this machine') : es ? 'fuera del presupuesto en esta máquina' : 'outside the budget on this machine'}
                </td>
              </tr>
              <tr>
                <td className="caos-col-text">{es ? 'Motor de cálculo' : 'Backend'}</td>
                <td>{out.backend.toUpperCase()}</td>
                <td className="caos-col-text" style={{ ...WRAP, whiteSpace: 'normal' }}>{out.fallbackReason ?? (out.backend === 'gpu' ? (es ? 'WebGPU coincidió con la CPU en la comprobación de la corrida' : 'WebGPU agreed with the CPU in the run\'s own check') : '-')}</td>
              </tr>
              <tr>
                <td className="caos-col-text">{es ? 'Dónde se fue el tiempo, última corrida (ms)' : 'Where the time went, last run (ms)'}</td>
                <td>{d(out.timing.methodMs, 0)}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                  {es ? `método ${d(out.timing.methodMs, 0)}, puntuación ${d(out.timing.scoreMs, 0)}, cesiones al ciclo de eventos ${d(out.timing.yieldMs, 0)}` : `method ${d(out.timing.methodMs, 0)}, scoring ${d(out.timing.scoreMs, 0)}, yields to the event loop ${d(out.timing.yieldMs, 0)}`}
                </td>
              </tr>
              <tr>
                <td className="caos-col-text">{es ? 'Métricas de la última corrida' : 'Metrics of the last run'}</td>
                <td>{n(out.metrics.efficiency)}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                  {es ? `eficiencia; uniformidad ${n(out.metrics.uniformity)}, desviación estándar relativa ${n(out.metrics.relStdPct)} por ciento` : `efficiency; uniformity ${n(out.metrics.uniformity)}, relative standard deviation ${n(out.metrics.relStdPct)} percent`}
                </td>
              </tr>
              {matrixSeconds !== null ? (
                <tr>
                  <td className="caos-col-text">{es ? 'Tiempo de la matriz del benchmark, G1 a 30 iteraciones (ms)' : 'Time in the benchmark matrix, G1 at 30 iterations (ms)'}</td>
                  <td>{d(matrixSeconds * 1000, 0)}</td>
                  <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                    {es ? 'otro motor (Python), otra grilla y otra máquina: no es la misma medición, se muestra solo para ubicar el orden de magnitud' : 'another engine (Python), another grid and another machine: not the same measurement, shown only to place the order of magnitude'}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </TableWrap>
      </PlotCard>
    </>
  );
}

export function LiveTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'In-browser timing of the live engine', es: 'Tiempo del motor en vivo, en el navegador' }} id="live" area="live" noRefsReason={{ en: 'the panel measures this browser; nothing in it comes from a paper', es: 'el panel mide este navegador; nada en él viene de un artículo' }}>
      <P
        en="The benchmark matrix is computed offline by the Python engine, and the site also carries a TypeScript port of the live methods that runs in a dedicated Web Worker, agrees with the Python reference to far less than the tolerance of its parity tests, and is what the workbench uses when a reader edits a case. This panel measures that engine in the reader's browser, on the default case of the index and on demand: nothing runs until the button is pressed, and the median of the timed runs is set against the budget that the case's lane gate declares for a live run. The figure is a property of this machine and this browser, not a claim about any other."
        es="La matriz del benchmark se calcula sin conexión con el motor de Python, y el sitio lleva además una versión en TypeScript de los métodos en vivo que corre en un Web Worker dedicado, coincide con la referencia de Python muy por debajo de la tolerancia de sus pruebas de paridad, y es lo que usa el banco de trabajo cuando un lector edita un caso. Este panel mide ese motor en el navegador del lector, sobre el caso por defecto del índice y a pedido: nada corre hasta que se pulsa el botón, y la mediana de las corridas cronometradas se contrasta con el presupuesto que la compuerta del carril del caso declara para una corrida en vivo. La cifra es propiedad de esta máquina y de este navegador, no una afirmación sobre otro."
      />
      <Note ids={['case-index', 'case-manifest']} />
      <Ready a={data.index}>{() => <LivePanel res={data.results.state === 'ready' ? data.results.data : null} />}</Ready>
    </DocSection>
  );
}
