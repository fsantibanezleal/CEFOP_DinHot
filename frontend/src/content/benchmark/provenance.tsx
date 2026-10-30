// Provenance (area `provenance`): per geometry, where the task comes from, what makes it hard and what is redistributed (nothing: every geometry is
// generated from seeds by the benchmark); the cells the document lists as not run, with the reason each method gave; and the ladder with the design
// record of each method. The geometry rows come from the results document; the difficulty source is the protocol's own description of each.
import { Cite, DocSection, useShellLang } from '@fasl-work/caos-app-shell';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { LADDER, MethodTable } from '../methodology/ladder';
import { nameOf, shownId, skippedIn, tierOf, TIER_SHORT, type Lang } from './data';
import { Note, Ready, TableWrap, useBench, WRAP } from './shared';

/** The difficulty of each geometry and the published task it is set against, from the benchmark protocol (the algorithms dossier D4.3 and D4.2). */
const SOURCE: Record<string, { en: string; es: string }> = {
  G1: { en: 'The 10 by 10 square array of Di Leonardo et al. 2007, the one published table that compares the classical methods on one task.', es: 'La matriz cuadrada de 10 por 10 de Di Leonardo et al. 2007, la única tabla publicada que compara los métodos clásicos en una misma tarea.' },
  G2: { en: 'Defined by the protocol: a ring of traps; no published task is set against it.', es: 'Definida por el protocolo: un anillo de trampas; no hay una tarea publicada con la que se contraste.' },
  G3: { en: 'Defined by the protocol: random positions with a minimum spacing, an array with no lattice symmetry.', es: 'Definida por el protocolo: posiciones aleatorias con un espaciamiento mínimo, una matriz sin simetría de red.' },
  G4: { en: 'The quasi-periodic set of Polin et al. 2005.', es: 'El conjunto cuasiperiódico de Polin et al. 2005.' },
  G5: { en: 'A three-dimensional lattice on three planes, the setting of the volumetric GS of Whyte and Courtial 2005; only the methods that handle traps off the focal plane run on it.', es: 'Una red tridimensional en tres planos, el escenario del GS volumétrico de Whyte y Courtial 2005; solo corren en ella los métodos que manejan trampas fuera del plano focal.' },
  G6: { en: 'Large and disordered arrays at the scale of Kim et al. 2019.', es: 'Matrices grandes y desordenadas a la escala de Kim et al. 2019.' },
  G7: { en: 'Shaped fields (ring, disc, line, Laguerre-Gaussian ring), the targets of Pasienski and DeVore 2008, for the methods that take a field and not a set of traps.', es: 'Campos con forma (anillo, disco, línea, anillo de Laguerre-Gauss), los objetivos de Pasienski y DeVore 2008, para los métodos que toman un campo y no un conjunto de trampas.' },
};

function Tables({ res }: { res: BenchmarkResults }) {
  const lang = useShellLang() as Lang;
  const es = lang === 'es';
  const skipped = skippedIn(res);
  return (
    <>
      <TableWrap>
        <table className="caos-table" data-state="ready" data-table="provenance-geometries">
          <caption>
            {es
              ? 'Las geometrías del benchmark: su fuente de dificultad y lo que se redistribuye. Ninguna geometría trae datos de terceros: el benchmark las genera de sus semillas, de modo que no hay nada que redistribuir fuera de las licencias del propio producto.'
              : 'The geometries of the benchmark: their source of difficulty and what is redistributed. No geometry brings third-party data: the benchmark generates each from its seeds, so there is nothing to redistribute beyond the licences of the product itself.'}
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
              <th>{es ? 'Trampas' : 'Traps'}</th>
              <th>{es ? 'Dimensiones' : 'Dimensions'}</th>
              <th className="caos-col-text">{es ? 'Conjunto de datos' : 'Dataset'}</th>
              <th className="caos-col-text">{es ? 'Fuente de la dificultad' : 'Source of the difficulty'}</th>
              <th className="caos-col-text">{es ? 'Redistribución' : 'Redistribution'}</th>
            </tr>
          </thead>
          <tbody>
            {res.geometries.map((g) => (
              <tr key={g.id} data-geometry={g.id}>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>
                  {g.id} {g.name[lang]}
                </td>
                <td>{g.n_traps}</td>
                <td>{g.dims}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? 'sintético, generado de semillas' : 'synthetic, generated from seeds'}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{SOURCE[g.id]?.[lang] ?? (es ? 'no registrada' : 'not recorded')}</td>
                <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{es ? 'ninguna (sin datos de terceros)' : 'none (no third-party data)'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <TableWrap>
        <table className="caos-table" data-state="ready" data-table="provenance-skipped">
          <caption>
            {es
              ? `Las ${skipped.length} celdas que el documento lista como no corridas, con la razón de cada método. Una celda no corrida no tiene fila y no es un cero.`
              : `The ${skipped.length} cells the document lists as not run, with the reason of each method. A cell not run has no row and is not a zero.`}
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{es ? 'Método' : 'Method'}</th>
              <th className="caos-col-text">{es ? 'Nivel' : 'Tier'}</th>
              <th className="caos-col-text">{es ? 'Geometría' : 'Geometry'}</th>
              <th className="caos-col-text">{es ? 'Razón' : 'Reason'}</th>
            </tr>
          </thead>
          <tbody>
            {skipped.length === 0 ? (
              <tr>
                <td colSpan={4} className="caos-col-text">{es ? 'El documento no lista celdas no corridas.' : 'The document lists no cells as not run.'}</td>
              </tr>
            ) : (
              skipped.map((s) => (
                <tr key={`${s.method}-${s.geometry}`}>
                  <td className="caos-col-text" style={{ whiteSpace: 'normal' }}>{shownId(s.method)} {nameOf(s.method, lang)}</td>
                  <td className="caos-col-text">{tierOf(s.method) ? TIER_SHORT[tierOf(s.method)!][lang] : '-'}</td>
                  <td className="caos-col-text">{s.geometry}</td>
                  <td className="caos-col-text" style={{ ...WRAP, whiteSpace: 'normal' }}>{s.reason[lang]}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </TableWrap>
    </>
  );
}

export function ProvenanceTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Where each row comes from', es: 'De dónde viene cada fila' }} id="provenance" area="provenance" refs={['dileonardo2007', 'polin2005', 'whyte2005', 'kim2019', 'pasienski2008']}>
      <P
        en={
          <>
            Each geometry is set against a task the literature already published, where one exists, so that the benchmark is read next to the references and not in isolation: the square array <Cite id="dileonardo2007" />, the quasi-periodic set <Cite id="polin2005" />, the three-dimensional lattice <Cite id="whyte2005" />, the large and disordered arrays <Cite id="kim2019" /> and the shaped fields <Cite id="pasienski2008" />. The values of those papers are not reproduced here: they were measured on other grids and with other budgets, and the protocol does not borrow them. What is borrowed is the task, and the result is DinHot&apos;s own matrix.
          </>
        }
        es={
          <>
            Cada geometría se contrasta con una tarea que la literatura ya publicó, donde existe, de modo que el benchmark se lee junto a las referencias y no aislado: la matriz cuadrada <Cite id="dileonardo2007" />, el conjunto cuasiperiódico <Cite id="polin2005" />, la red tridimensional <Cite id="whyte2005" />, las matrices grandes y desordenadas <Cite id="kim2019" /> y los campos con forma <Cite id="pasienski2008" />. Los valores de esos artículos no se reproducen aquí: se midieron en otras grillas y con otros presupuestos, y el protocolo no los toma prestados. Lo que se toma es la tarea, y el resultado es la matriz propia de DinHot.
          </>
        }
      />
      <Note ids={['benchmark-results']} />
      <Ready a={data.results}>{(res) => <Tables res={res} />}</Ready>
      <h3>{useShellLang() === 'es' ? 'La escalera de métodos' : 'The method ladder'}</h3>
      <MethodTable ids={LADDER.map((r) => r.id)} />
    </DocSection>
  );
}
