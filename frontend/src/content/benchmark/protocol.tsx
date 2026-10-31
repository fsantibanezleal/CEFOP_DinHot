// The protocol topic: how every cell of the benchmark is measured, read from the protocol block of the results document (grids, seeds,
// budgets, device) and from the ladder, so a protocol change in the pipeline changes the page and never the other way round.
import { Cite, DocSection, Equation, useShellLang } from '@fasl-work/caos-app-shell';
import type { BenchmarkResults } from '../../lib/contract.types';
import { Note, Ready, TableWrap, useBench } from './shared';
import { P } from '../bi';
import { budgetText, budgetsOf, methodsIn, skippedIn, kindOf, KIND_ORDER, KIND_TEXT } from './data';

function ProtocolBody({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang();
  const es = lang === 'es';
  const p = res.protocol;
  const budgets = budgetsOf(res);
  const methods = methodsIn(res);
  const ran = new Set(res.rows.map((r) => r.method));
  const tuned = new Set(res.rows.filter((r) => r.params === 'tuned').map((r) => r.method));
  const list = (xs: string[]) => xs.join(', ');
  const rows: [string, string, string][] = [
    [es ? 'Tamaño de grilla de la SLM (píxeles por lado)' : 'SLM grid (pixels per side)', list(p.grids.map(String)), es ? 'Cada celda se corre en estos tamaños; la escala de los valores publicados (768 por lado) no se reproduce.' : 'Each cell is run at these sizes; the scale of the published values (768 per side) is not reproduced.'],
    [es ? 'Semillas por celda' : 'Seeds per cell', String(p.seeds), es ? 'La fase inicial aleatoria de todos los métodos sale de la misma semilla; se informa la mediana y el rango intercuartil.' : 'The random initial phase of every method comes from the same seed; the median and the inter-quartile range are reported.'],
    [es ? 'Presupuestos de iteraciones' : 'Iteration budgets', list(p.budgets.iterations.map(String)), es ? 'Corridas de exactamente esa longitud.' : 'Runs of exactly that length.'],
    [es ? 'Presupuestos de reloj' : 'Wall-clock budgets', list(p.budgets.time_s.map((s) => budgetText({ kind: 'time', value: s })[lang])), es ? 'Las dos primeras filas son corridas con tope de tiempo; la última es la fila convergida (se alcanza antes el tope).' : 'The first rows are time-capped runs; the last is the converged row (the cap is reached first).'],
    [es ? 'Presupuestos presentes en las filas' : 'Budgets present in the rows', list(budgets.map((b) => budgetText(b)[lang])), es ? 'Leídos de las filas del documento.' : 'Read from the rows of the document.'],
    [es ? 'Geometrías' : 'Geometries', list(res.geometries.map((g) => g.id)), es ? 'Cada una con su nombre y su número de trampas en la pestaña de resultados.' : 'Each with its name and its trap count on its results tab.'],
    [es ? 'Métodos con alguna fila' : 'Methods with at least one row', `${ran.size} ${es ? 'de' : 'of'} ${methods.length}`, es ? 'Un método sin fila en una celda está en la lista de celdas no corridas, con su razón.' : 'A method with no row in a cell is on the list of cells not run, with its reason.'],
    [es ? 'Métodos con filas ajustadas' : 'Methods with tuned rows', tuned.size ? list([...tuned].sort()) : '-', es ? 'Solo un método que declara una rejilla de ajuste tiene filas ajustadas, y con el mismo número de corridas de ajuste que los demás.' : 'Only a method that declares a tuning grid has tuned rows, with the same number of tuning runs as the others.'],
    [es ? 'Celdas no corridas' : 'Cells not run', String(skippedIn(res).length), es ? 'Cada una con la razón del método; aparecen en la tabla de la geometría y en la de procedencia.' : 'Each with the reason of the method; they are listed in the table of the geometry and in the provenance table.'],
  ];
  const counts = KIND_ORDER.map((kind) => ({ kind, n: methods.filter((m) => kindOf(m) === kind).length }));
  return (
    <>
      <TableWrap>
        <table className="caos-table" data-state="ready">
          <caption>
            {es
              ? `El protocolo de la versión ${res.engine_version} del motor, tal como lo declara el documento de resultados.`
              : `The protocol of engine version ${res.engine_version}, as the results document declares it.`}
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Elemento' : 'Item'}</th>
              <th className="caos-col-text">{es ? 'Valor' : 'Value'}</th>
              <th className="caos-col-text">{es ? 'Lectura' : 'Reading'}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, v, r]) => (
              <tr key={k}>
                <td className="caos-col-text">{k}</td>
                <td className="caos-col-text" style={{ overflowWrap: 'anywhere' }}>{v}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{r}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <p className="caos-plot-note" lang={lang}>
        {es ? 'Dispositivo: ' : 'Device: '}
        {p.device[lang]}
      </p>
      <p className="caos-plot-note" lang={lang}>
        {es ? 'Métodos por tipo en este documento: ' : 'Methods per kind in this document: '}
        {counts.map((c) => `${KIND_TEXT[c.kind][lang]} ${c.n}`).join('; ')}.
      </p>
    </>
  );
}

export function ProtocolTopic() {
  const { data } = useBench();
  const es = useShellLang() === 'es';
  return (
    <DocSection title={{ en: 'The protocol', es: 'El protocolo' }} id="protocol" area="results" refs={['dileonardo2007', 'kim2019', 'schroff2023', 'pasienski2008', 'slmsuite']}>
      <P
        en={
          <>
            The benchmark exists because no published comparison puts the methods of a hologram engine on one array with one set of seeds: the published tables report each method at the setting its authors chose, on grids of their own, at an iteration count or a search length that differs from method to method <Cite id="dileonardo2007" /> <Cite id="pasienski2008" />. DinHot therefore measures its own matrix. Every method of the ladder, published and proposed, runs on every geometry that its target kind accepts, with the same random starts, the same metrics and the same budgets, and the page reads the result from the committed document, so a number on this page is a number of that document and of no other source.
          </>
        }
        es={
          <>
            El benchmark existe porque ninguna comparación publicada pone los métodos de un motor de hologramas sobre una misma matriz con un mismo conjunto de semillas: las tablas publicadas informan cada método con el ajuste que eligieron sus autores, sobre grillas propias y con un número de iteraciones o una longitud de búsqueda que cambia de un método a otro <Cite id="dileonardo2007" /> <Cite id="pasienski2008" />. DinHot mide entonces su propia matriz. Cada método de la escalera, publicado y propuesto, corre en cada geometría que su tipo de objetivo acepta, con los mismos arranques aleatorios, las mismas métricas y los mismos presupuestos, y la página lee el resultado del documento versionado, de modo que un número de esta página es un número de ese documento y de ninguna otra fuente.
          </>
        }
      />
      <P
        en={
          <>
            Fairness is a rule of the protocol and not a habit of the page. Every method is reported twice, with the default parameters of its own paper and with a small tuning grid shared by all the methods that have one, and both are labelled wherever they appear; a tuned result is never set against an unlabelled default, because a family that is tuned to its best point and compared with another at its default would win by the tuning and not by the method. Each hologram is scored from its final phase against the device it was made for, which for the device rows is the C08 device with its quantization, crosstalk, fill factor and flicker <Cite id="schroff2023" />, so a method that ignores the device is measured by what the device does to it.
          </>
        }
        es={
          <>
            La equidad es una regla del protocolo y no un hábito de la página. Cada método se informa dos veces, con los parámetros por defecto de su propio artículo y con una pequeña rejilla de ajuste común a todos los métodos que la tienen, y ambos se rotulan donde aparecen; un resultado ajustado nunca se contrasta con un valor por defecto sin rótulo, porque una familia ajustada a su mejor punto y comparada con otra en su valor por defecto ganaría por el ajuste y no por el método. Cada holograma se evalúa desde su fase final contra el dispositivo para el que se hizo, que en las filas con dispositivo es el dispositivo C08 con su cuantización, su diafonía, su factor de llenado y su parpadeo <Cite id="schroff2023" />, de modo que un método que ignora el dispositivo se mide por lo que el dispositivo le hace.
          </>
        }
      />
      <P
        en={
          <>
            Two quantities decide most of the comparisons below. The uniformity factor of a challenger against its baseline is the ratio of their relative standard deviations, and the efficiency ratio is the ratio of their efficiencies; a claim about a proposed method states a threshold on both, so a method that is uniform because it wastes the light does not pass. The efficiency-uniformity trade-off of a method that returns a whole front is compared by hypervolume against the point (0, 0), the area of the union of the rectangles under its points, which is the one scalar that grows when a front moves toward better efficiency, better uniformity or both. The medians over the seeds of the document, and not single runs, feed both.
          </>
        }
        es={
          <>
            Dos cantidades deciden la mayor parte de las comparaciones siguientes. El factor de uniformidad de un retador frente a su línea base es el cociente de sus desviaciones estándar relativas, y la razón de eficiencia es el cociente de sus eficiencias; una afirmación sobre un método propuesto fija un umbral en ambos, de modo que un método uniforme porque desperdicia la luz no la cumple. El compromiso eficiencia-uniformidad de un método que entrega un frente completo se compara por hipervolumen respecto del punto (0, 0), el área de la unión de los rectángulos bajo sus puntos, que es el único escalar que crece cuando un frente se mueve hacia mejor eficiencia, mejor uniformidad o ambas. Las medianas sobre las semillas del documento, y no corridas sueltas, alimentan ambos.
          </>
        }
      />
      <Equation
        tex={String.raw`F_\sigma = \frac{\sigma_{\mathrm{base}}}{\sigma_{\mathrm{chal}}}, \qquad R_e = \frac{e_{\mathrm{chal}}}{e_{\mathrm{base}}}, \qquad \mathrm{HV} = \Bigl|\,\bigcup_i \,[0, e_i]\times[0, u_i]\Bigr|`}
        caption={
          es
            ? 'Las cantidades de las afirmaciones. σ es la desviación estándar relativa de las intensidades de las trampas en porcentaje (menor es más uniforme), e la eficiencia, u la uniformidad, cada una mediana sobre las semillas; los subíndices nombran al retador (chal) y a su línea base (base) en la misma celda. F_σ mayor que 1 significa que el retador es más uniforme, R_e menor que 1 que gasta luz para lograrlo, y HV es el área de la unión de los rectángulos bajo los puntos (e_i, u_i) de un conjunto de métodos.'
            : 'The quantities of the claims. σ is the relative standard deviation of the trap intensities in percent (lower is more uniform), e the efficiency, u the uniformity, each a median over the seeds; the subscripts name the challenger (chal) and its baseline (base) in the same cell. F_σ above 1 means the challenger is more uniform, R_e below 1 means it spends light to get there, and HV is the area of the union of the rectangles under the points (e_i, u_i) of one method set.'
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <ProtocolBody res={res} />}</Ready>
    </DocSection>
  );
}
