// The views of the Experiments page: the section of one case (its question, its setup, its result against the anchor and the table of that
// result), the chart and table of the methods of a case, the camera-loop chart and the filling chart. Every number is formatted by the shell's
// `formatNumber` from the artifact it comes from; the text is the bilingual template of `cases.ts` filled at run time.
import { BarChart, DocSection, formatNumber, NBSP, SubTabs, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import type { AbsentCase } from '../../api/artifacts';
import type { Text } from '../../lib/contract.types';
import { methodLabel } from '../../workbench/model';
import { bakeRows, CASES, common, type Fmt, type Lang, type Row } from './cases';
import { Scroll } from './context';
import {
  feedbackSteps,
  fill,
  isShaped,
  methodIds,
  rangeScore,
  type CaseView,
} from './data';

const WRAP = { overflowWrap: 'anywhere' } as const;

/** The formatters of the displayed language. */
export function useFmtObj(caseIds: string[]): Fmt {
  const lang = useShellLang() as Lang;
  return useMemo<Fmt>(() => {
    const n: Fmt['n'] = (v, o) => (v === null || v === undefined || !Number.isFinite(v) ? '-' : formatNumber(v, lang, { grouping: false, ...(o ?? { digits: 3 }) }));
    return { lang, caseIds, n, pct: (v, o) => (v === null || v === undefined || !Number.isFinite(v) ? '-' : `${n(v, o)}${NBSP}%`) };
  }, [lang, caseIds]);
}

/** The citation ids a case section cites (all in `citations/methodology.ts` or `citations/experiments.ts`). */
export const CASE_REFS: Record<string, string[]> = {
  C01_square_grid: ['nogrette2014', 'tolic2006'],
  C02_grid_feedback: ['nogrette2014'],
  C03_large_array: ['kim2019', 'ebadi2021', 'grimm2000'],
  C13_disordered_array: ['kim2019'],
  C12_calibration: ['dileonardo2007', 'bianchi2010'],
  C04_disc_crosstalk: ['schroff2023', 'pasienski2008'],
  C05_multiplane_vortices: ['polin2005'],
  C06_vortex_ring_line: ['polin2005'],
  C14_volume_learned: ['eybposh2020', 'whyte2005'],
  C07_high_na: ['leutenegger2006'],
  C08_device_limited: ['schroff2023'],
  C09_aberrated: ['nogrette2014', 'noll1976'],
  C10_rearrangement: ['barredo2016', 'endres2016', 'lee2017'],
  C11_outside_field: ['schroff2023'],
};

/** A producer's Spanish sentence writes its decimals with a point (the refusal reason of the index does): shown with the Spanish comma. */
export const spanishDecimals = (s: string, lang: Lang): string => (lang === 'es' ? s.replace(/(\d)\.(\d)/g, '$1,$2') : s);

const T = (t: Text, lang: Lang) => (lang === 'es' ? t.es : t.en);

/** A data table with its head and rows in the displayed language. */
function RowsTable({ rows, lang }: { rows: Row[]; lang: Lang }) {
  if (!rows.length) return null;
  const es = lang === 'es';
  return (
    <Scroll>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th className="caos-col-text">{es ? 'Cantidad' : 'Quantity'}</th>
            <th className="caos-col-text">{es ? 'Valor publicado y condiciones' : 'Published value and conditions'}</th>
            <th>{es ? 'Rango verificado por la generación' : 'Range checked by the bake'}</th>
            <th>{es ? 'Medido aquí' : 'Measured here'}</th>
            <th className="caos-col-text">{es ? 'Lectura' : 'Reading'}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="caos-col-text" style={WRAP}>{r.label}</td>
              <td className="caos-col-text" style={{ ...WRAP, whiteSpace: 'normal' }}><span translate="no">{r.published ?? '-'}</span></td>
              <td>{r.range ?? '-'}</td>
              <td>{r.here}</td>
              <td className="caos-col-text" style={WRAP}>{r.reading ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Scroll>
  );
}

/** A generic text for a case this page has no written text for (a case added to the index later): it reads the manifest's own words. */
export const GENERIC = {
  setup: {
    en: '{title} is a case of the category {category}, run on {nm} methods with the seed {seed} and a budget of {iters} iterations; the reference method is {ref}. Its optics are {wl} nm through a lens of {focal} mm and numerical aperture {na}, on an SLM of {npix} by {npix} pixels. The band the case declares for itself reads: {band}',
    es: '{title} es un caso de la categoría {category}, corrido con {nm} métodos, la semilla {seed} y un presupuesto de {iters} iteraciones; el método de referencia es {ref}. Su óptica es de {wl} nm a través de un lente de {focal} mm y apertura numérica {na}, sobre un SLM de {npix} por {npix} píxeles. La banda que el caso declara para sí dice: {band}',
  },
  result: {
    en: 'The reference method {ref} reaches an efficiency of {refEff}, a uniformity of {refU} and a relative standard deviation of {refSd} percent, and the bake names {best} as the most uniform method among those that keep at least half the best efficiency. {okAll} of {ofAll} methods with checked ranges sit inside all of them. The anchor of the case is {anchor}; this page has no written comparison for this case yet, so the table beside this text shows only the ranges the bake checked and what it measured.',
    es: 'El método de referencia {ref} alcanza una eficiencia de {refEff}, una uniformidad de {refU} y una desviación estándar relativa de {refSd} por ciento, y la generación nombra a {best} como el método más uniforme entre los que conservan al menos la mitad de la mejor eficiencia. {okAll} de {ofAll} métodos con rangos verificados caen dentro de todos ellos. El ancla del caso es {anchor}; esta página aún no tiene una comparación escrita para este caso, así que la tabla junto a este texto muestra solo los rangos que verificó la generación y lo que midió.',
  },
};

/** The section of one baked case, area `question`: two dense paragraphs, the anchor line, the flags of the manifest and the table. */
export function CaseSection({ view, caseIds }: { view: CaseView; caseIds: string[] }) {
  const f = useFmtObj(caseIds);
  const lang = f.lang;
  const id = view.manifest.case_id;
  const text = CASES[id];
  const m = view.manifest;
  const base = common(view, f);
  const anchor = T(m.anchor.source, lang);
  const values = text
    ? text.vals(view, f)
    : { ...base, title: T(m.title, lang), category: T(m.category, lang), band: T(m.expected_band, lang), anchor };
  const setupT = text ? text.setup : GENERIC.setup;
  const resultT = text ? text.result : GENERIC.result;
  const p1 = `${text ? `${T(text.question, lang)} ` : ''}${fill(T(setupT, lang), values)}`;
  const p2 = fill(T(resultT, lang), values);
  const rows = [...bakeRows(view, f), ...(text?.extra?.(view, f) ?? [])];
  const refs = CASE_REFS[id];
  const flags = m.flags.map((x) => x.flag).filter((x) => !/^forward form chosen/.test(x));
  return (
    <DocSection
      title={{ en: `${id.slice(0, 3)}: ${m.title.en}`, es: `${id.slice(0, 3)}: ${m.title.es}` }}
      id={id}
      area="question"
      refs={refs}
      noRefsReason={refs ? undefined : { en: 'its anchor is quoted from the manifest of the case', es: 'su ancla se cita del manifiesto del caso' }}
    >
      <p lang={lang}>{p1}</p>
      <p lang={lang}>{p2}</p>
      <p className="caos-plot-note" lang={lang} style={WRAP}>
        {lang === 'es' ? 'Ancla: ' : 'Anchor: '}
        <span translate="no">{anchor}</span>
        {m.anchor.url ? (
          <>
            {' '}
            <a href={m.anchor.url} target="_blank" rel="noreferrer">
              {lang === 'es' ? 'fuente' : 'source'}
            </a>
          </>
        ) : null}
        {'. '}
        {lang === 'es' ? 'Origen de los datos: ' : 'Data origin: '}
        {m.real_or_synthetic === 'synthetic' ? (lang === 'es' ? 'sintético (los parámetros son declarados, no hay muestra medida).' : 'synthetic (the parameters are stated; no measured sample is used).') : m.real_or_synthetic}
      </p>
      {flags.length > 0 && (
        <ul lang={lang}>
          {flags.map((x) => (
            <li key={x} style={WRAP}>
              {lang === 'es' ? 'Bandera del manifiesto (en inglés, tal como la escribe la generación): ' : 'Flag of the manifest: '}
              <span lang="en" translate="no">{x}</span>
            </li>
          ))}
        </ul>
      )}
      <RowsTable rows={rows} lang={lang} />
    </DocSection>
  );
}

/** The refusal and unavailability texts: the control case needs a written reading too (two dense paragraphs). */
export const REFUSED = {
  refused: {
    p1: {
      en: '{title} is the refusal case, the control that every case set needs. A trap beyond the unaliased field of view lies in the replica of the focal grid, so any hologram that placed light there would also place it inside the field. The product therefore refuses the record at the door, names the bound and never computes it: the case index lists it with the status {status}, and no manifest and no trace exist for it, which is the whole artifact of this case.',
      es: '{title} es el caso de rechazo, el control que todo conjunto de casos necesita. Una trampa más allá del campo de visión sin aliasing cae en la réplica de la grilla focal, así que cualquier holograma que pusiera luz allí la pondría también dentro del campo. El producto por eso rechaza el registro en la puerta, nombra la cota y nunca lo calcula: el índice de casos lo lista con el estado {status}, y no existen manifiesto ni traza para él, que es todo el artefacto de este caso.',
    },
    p2: {
      en: 'The reason the index gives is: {reason}. This is an error state and not a metric, so no method ran, no efficiency or uniformity exists for the case and no chart can be drawn; the page shows the reason in place of one. The anchor is the pixel relation of the replica period, the wavelength times the focal length over the pixel pitch, taken from Schroff et al. 2023, which fixes the half field at which the refusal happens.',
      es: 'La razón que da el índice es: {reason}. Es un estado de error y no una métrica, así que ningún método corrió, no existe eficiencia ni uniformidad para el caso y no se puede dibujar ningún gráfico; la página muestra la razón en su lugar. El ancla es la relación de píxeles del período de la réplica, la longitud de onda por la distancia focal sobre el paso del píxel, tomada de Schroff et al. 2023, que fija el medio campo en que ocurre el rechazo.',
    },
  },
  other: {
    p1: {
      en: '{title} is listed by the case index, but its artifacts are not available in this build, so there is nothing of it to measure on this page. The readiness document of the build is the record of that state, and this section shows its reason instead of an empty chart, because a chart drawn over missing data would say something the bake did not say.',
      es: '{title} figura en el índice de casos, pero sus artefactos no están disponibles en esta versión, así que no hay nada de él que medir en esta página. El documento de disponibilidad de la versión es el registro de ese estado, y esta sección muestra su razón en lugar de un gráfico vacío, porque un gráfico dibujado sobre datos ausentes diría algo que la generación no dijo.',
    },
    p2: {
      en: 'The reason given is: {reason}. When the bake writes the artifacts of this case, this section reads them like those of the other cases and replaces this note with the question, the setup and the table of results against the anchor; no text is kept by hand for a number that the artifacts do not yet hold, and the case stays in the matrix with its status either way.',
      es: 'La razón dada es: {reason}. Cuando la generación escriba los artefactos de este caso, esta sección los leerá como los de los otros casos y reemplazará esta nota por la pregunta, el montaje y la tabla de resultados frente al ancla; no se guarda a mano texto para un número que los artefactos aún no tienen, y el caso queda en la matriz con su estado de todas formas.',
    },
  },
};

/** The section of a case that has no manifest: refused by contract 1, or absent for a reason the readiness document gives. */
export function AbsentSection({ item, status, refs }: { item: AbsentCase; status: string; refs?: string[] }) {
  const lang = useShellLang() as Lang;
  const refused = status === 'refused';
  const t = refused ? REFUSED.refused : REFUSED.other;
  const vals = { title: T(item.title, lang), status, reason: spanishDecimals(T(item.reason, lang), lang).replace(/[.\s]+$/, '') };
  return (
    <DocSection
      title={{ en: `${item.caseId.slice(0, 3)}: ${item.title.en}`, es: `${item.caseId.slice(0, 3)}: ${item.title.es}` }}
      id={item.caseId}
      area="question"
      refs={refused ? (refs ?? CASE_REFS[item.caseId]) : undefined}
      noRefsReason={refused ? undefined : { en: 'it cites the readiness document of the build', es: 'cita el documento de disponibilidad de la versión' }}
    >
      <p lang={lang}>{fill(T(t.p1, lang), vals)}</p>
      <p lang={lang} data-state="unavailable">{fill(T(t.p2, lang), vals)}</p>
    </DocSection>
  );
}

const EFF: Text = { en: 'Efficiency', es: 'Eficiencia' };
const UNI: Text = { en: 'Uniformity', es: 'Uniformidad' };
const ERR: Text = { en: 'Signal error', es: 'Error de señal' };

/** The chart and table of the methods of one case: efficiency and uniformity for traps, efficiency and signal error for a shaped potential. */
function MethodsPanel({ view, lang }: { view: CaseView; lang: Lang }) {
  const f = useFmtObj([]);
  const m = view.manifest;
  const ids = methodIds(m);
  const shaped = isShaped(m);
  const es = lang === 'es';
  const data = ids.flatMap((id) => {
    const v = m.methods[id];
    const group = { id, label: methodLabel(id) };
    return shaped
      ? [{ id: `${id}-e`, label: EFF, value: v.efficiency, tone: 'accent' as const, group }]
      : [
          { id: `${id}-e`, label: EFF, value: v.efficiency, tone: 'accent' as const, group },
          { id: `${id}-u`, label: UNI, value: v.uniformity, tone: 'good' as const, group },
        ];
  });
  const errData = ids.map((id) => ({ id: `${id}-s`, label: methodLabel(id), value: m.methods[id].rel_std_pct, tone: 'warn' as const }));
  const title = { en: `${m.title.en}: methods`, es: `${m.title.es}: métodos` };
  return (
    <div>
      <BarChart
        title={shaped ? { en: `${title.en}, efficiency`, es: `${title.es}, eficiencia` } : { en: `${title.en}, efficiency and uniformity`, es: `${title.es}, eficiencia y uniformidad` }}
        data={data}
        axis={{ label: shaped ? EFF : { en: 'Fraction', es: 'Fracción' }, format: { decimals: 2 }, range: [0, 1] }}
        orientation="horizontal"
        legend={shaped ? undefined : [{ tone: 'accent', label: EFF }, { tone: 'good', label: UNI }]}
      />
      {shaped && (
        <BarChart
          title={{ en: `${title.en}, signal error`, es: `${title.es}, error de señal` }}
          data={errData}
          axis={{ label: ERR, unit: { en: 'percent', es: 'por ciento' }, format: { digits: 3 } }}
          orientation="horizontal"
        />
      )}
      <Scroll>
        <table className="caos-table" data-state="ready">
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
              <th className="caos-col-text">{es ? 'Carril' : 'Lane'}</th>
              <th>{EFF[lang]}</th>
              <th>{shaped ? es ? 'Error de señal (por ciento)' : 'Signal error (percent)' : UNI[lang]}</th>
              {!shaped && <th>{es ? 'Desviación relativa (por ciento)' : 'Relative spread (percent)'}</th>}
              <th>{es ? 'Orden cero' : 'Zero order'}</th>
              <th>{es ? 'Fantasmas' : 'Ghost'}</th>
              <th>{es ? 'Dentro del rango' : 'Inside the range'}</th>
            </tr>
          </thead>
          <tbody>
            {ids.map((id) => {
              const v = m.methods[id];
              const sc = rangeScore(m, id);
              return (
                <tr key={id}>
                  <td className="caos-col-text" style={WRAP}>{T(methodLabel(id), lang)}</td>
                  <td className="caos-col-text">{v.lane}</td>
                  <td>{f.n(v.efficiency, { decimals: 3 })}</td>
                  <td>{shaped ? f.n(v.rel_std_pct, { digits: 4 }) : f.n(v.uniformity, { decimals: 3 })}</td>
                  {!shaped && <td>{f.n(v.rel_std_pct, { digits: 3 })}</td>}
                  <td>{f.n(v.zero_order, { decimals: 3 })}</td>
                  <td>{f.n(v.ghost, { decimals: 3 })}</td>
                  <td>{sc.of ? `${f.n(sc.ok, { decimals: 0 })} / ${f.n(sc.of, { decimals: 0 })}` : '-'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Scroll>
      {m.params.rearrangement && (
        <p className="caos-plot-note" lang={lang}>
          {es
            ? `El método de referencia ${m.params.reference_method} ordena átomos e ilumina solo los sitios objetivo: sus métricas de trampas sobre todos los sitios no son un resultado y su rango verificado es solo el de eficiencia.`
            : `The reference method ${m.params.reference_method} sorts atoms and lights the target sites only: its trap metrics over all the sites are not a result, and its checked range is the efficiency alone.`}
        </p>
      )}
    </div>
  );
}

/** The results of a family of cases: one tab per baked case, each with the chart and the table of its methods. */
export function FamilyResults({ views, lang, children }: { views: CaseView[]; lang: Lang; children?: React.ReactNode }) {
  return (
    <DocSection
      title={{ en: 'What every method measured', es: 'Lo que midió cada método' }}
      id="methods"
      noRefsReason={{ en: 'the results are read from the committed bake', es: 'los resultados se leen de la generación versionada' }}
    >
      <SubTabs
        ariaLabel={lang === 'es' ? 'Casos de la familia' : 'Cases of the family'}
        tabs={views.map((v) => ({ id: v.manifest.case_id, label: v.manifest.case_id.slice(0, 3), content: <MethodsPanel view={v} lang={lang} /> }))}
      />
      {children}
    </DocSection>
  );
}

/** The camera loop of the cases that have one: measured spread by step, with the published final spread as a reference line. */
export function FeedbackChart({ views, marks, lang }: { views: CaseView[]; marks: { y: number; label: Text }[]; lang: Lang }) {
  const f = useFmtObj([]);
  const loops = views.filter((v) => feedbackSteps(v.trace).length > 1);
  if (!loops.length) return null;
  const longest = Math.max(...loops.map((v) => feedbackSteps(v.trace).length));
  const xs = Array.from({ length: longest }, (_, k) => k);
  const tones = ['--color-accent', '--color-good', '--color-warn'] as const;
  const es = lang === 'es';
  return (
    <div>
      <UPlotChart
        title={{ en: 'Measured spread of the traps by camera step', es: 'Dispersión medida de las trampas por paso de cámara' }}
        height={300}
        x={{ values: xs, label: { en: 'Camera step', es: 'Paso de cámara' }, format: { decimals: 0, grouping: false } }}
        y={{ label: { en: 'Measured spread', es: 'Dispersión medida' }, unit: { en: 'percent', es: 'por ciento' }, log: true, format: { digits: 2 } }}
        series={loops.map((v, i) => {
          const s = feedbackSteps(v.trace);
          return {
            id: v.manifest.case_id,
            label: { en: `${v.manifest.case_id.slice(0, 3)} ${v.manifest.title.en}`, es: `${v.manifest.case_id.slice(0, 3)} ${v.manifest.title.es}` },
            values: xs.map((k) => (k < s.length ? Math.max(s[k].rel_std_pct, 1e-3) : null)),
            color: tones[i % tones.length],
            dots: true,
          };
        })}
        yMarks={marks.map((m) => ({ ...m, tone: 'good' as const }))}
        solo
        readout={(k) =>
          loops
            .map((v) => {
              const s = feedbackSteps(v.trace);
              return k < s.length ? `${v.manifest.case_id.slice(0, 3)}: ${f.pct(s[k].rel_std_pct, { digits: 3 })}` : null;
            })
            .filter(Boolean)
            .join('; ') || (es ? 'sin dato' : 'no data')
        }
      />
      <Scroll>
        <table className="caos-table" data-state="ready">
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Caso' : 'Case'}</th>
              <th>{es ? 'Pasos' : 'Steps'}</th>
              <th>{es ? 'Antes (por ciento)' : 'Before (percent)'}</th>
              <th>{es ? 'Tras un paso (por ciento)' : 'After one step (percent)'}</th>
              <th>{es ? 'Al final (por ciento)' : 'At the end (percent)'}</th>
              <th>{es ? 'Eficiencia al final' : 'Efficiency at the end'}</th>
            </tr>
          </thead>
          <tbody>
            {loops.map((v) => {
              const s = feedbackSteps(v.trace);
              return (
                <tr key={v.manifest.case_id}>
                  <td className="caos-col-text">{`${v.manifest.case_id.slice(0, 3)} ${T(v.manifest.title, lang)}`}</td>
                  <td>{f.n(s.length - 1, { decimals: 0 })}</td>
                  <td>{f.n(s[0].rel_std_pct, { digits: 3 })}</td>
                  <td>{f.n(s[1].rel_std_pct, { digits: 3 })}</td>
                  <td>{f.n(s[s.length - 1].rel_std_pct, { digits: 3 })}</td>
                  <td>{f.n(s[s.length - 1].efficiency, { decimals: 3 })}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Scroll>
    </div>
  );
}

/** The rearrangement sequence: filling of the target by frame, with the moving traps and the occupied sites of each frame in the table. */
export function FillingChart({ view, lang }: { view: CaseView; lang: Lang }) {
  const f = useFmtObj([]);
  const fr = view.trace.rearrangement;
  if (!fr) return null;
  const es = lang === 'es';
  const ms = fr.frames.map((x) => x.t_s * 1000);
  return (
    <div>
      <UPlotChart
        title={{ en: 'Filling of the target by frame', es: 'Llenado del objetivo por cuadro' }}
        height={280}
        x={{ values: ms, label: { en: 'Time', es: 'Tiempo' }, unit: { en: 'ms', es: 'ms' }, format: { digits: 3 } }}
        y={{ label: { en: 'Filling of the target', es: 'Llenado del objetivo' }, format: { decimals: 2 }, range: [0, 1.05] }}
        series={[{ label: { en: 'Filling', es: 'Llenado' }, values: fr.filling.slice(0, ms.length), color: '--color-accent', dots: true }]}
        readout={(k) => {
          const fm = fr.frames[k];
          return es
            ? `cuadro ${k}: ${f.n(fm.moving.length, { decimals: 0 })} trampas en movimiento, ${f.n(fm.occupied.length, { decimals: 0 })} sitios ocupados, llenado ${f.n(fr.filling[k], { decimals: 3 })}`
            : `frame ${k}: ${f.n(fm.moving.length, { decimals: 0 })} moving traps, ${f.n(fm.occupied.length, { decimals: 0 })} occupied sites, filling ${f.n(fr.filling[k], { decimals: 3 })}`;
        }}
      />
      <Scroll>
        <table className="caos-table" data-state="ready">
          <thead>
            <tr>
              <th>{es ? 'Cuadro' : 'Frame'}</th>
              <th>{es ? 'Tiempo (ms)' : 'Time (ms)'}</th>
              <th>{es ? 'Trampas en movimiento' : 'Moving traps'}</th>
              <th>{es ? 'Sitios ocupados' : 'Occupied sites'}</th>
              <th>{es ? 'Llenado del objetivo' : 'Filling of the target'}</th>
            </tr>
          </thead>
          <tbody>
            {fr.frames.map((fm, k) => (
              <tr key={k}>
                <td>{f.n(k, { decimals: 0 })}</td>
                <td>{f.n(ms[k], { digits: 3 })}</td>
                <td>{f.n(fm.moving.length, { decimals: 0 })}</td>
                <td>{f.n(fm.occupied.length, { decimals: 0 })}</td>
                <td>{f.n(fr.filling[k], { decimals: 3 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Scroll>
    </div>
  );
}

