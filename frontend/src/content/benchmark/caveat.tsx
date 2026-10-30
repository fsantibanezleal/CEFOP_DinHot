// The limits of the comparison (area `caveat`): one honest callout, with the figures that the document itself declares (seeds, grids, the number of
// cells not run) read at run time, and the limits that are properties of the method of the benchmark and not of its numbers.
import { Callout, DocSection, useShellLang } from '@fasl-work/caos-app-shell';
import type { BenchmarkResults } from '../../lib/contract.types';
import { P } from '../bi';
import { skippedIn } from './data';
import { Note, Ready, useBench } from './shared';

function Limits({ res }: { res: BenchmarkResults }) {
  const es = useShellLang() === 'es';
  const p = res.protocol;
  const skipped = skippedIn(res).length;
  const tuned = [...new Set(res.rows.filter((r) => r.params === 'tuned').map((r) => r.method))].sort();
  const items: { en: string; es: string }[] = [
    {
      en: `The numbers are medians over ${p.seeds} seeds per cell on the SLM grids ${p.grids.join(', ')} of this document; the published tables were measured on larger grids, so the ordering of the methods is what transfers and not the value of a metric.`,
      es: `Los números son medianas sobre ${p.seeds} semillas por celda en las grillas de SLM ${p.grids.join(', ')} de este documento; las tablas publicadas se midieron en grillas mayores, de modo que lo que se transfiere es el orden de los métodos y no el valor de una métrica.`,
    },
    {
      en: 'Times are wall-clock seconds of the machine that ran the benchmark and differ between runs and machines; they rank the methods on that machine and say nothing about another.',
      es: 'Los tiempos son segundos de reloj de la máquina que corrió el benchmark y difieren entre corridas y máquinas; ordenan los métodos en esa máquina y no dicen nada sobre otra.',
    },
    {
      en: 'Every geometry is synthetic and the C08 device is a model whose crosstalk parameters come from a published calibration; no row is a measurement on a physical SLM, and a method that wins here can lose on a device the model does not describe.',
      es: 'Toda geometría es sintética y el dispositivo C08 es un modelo cuyos parámetros de diafonía vienen de una calibración publicada; ninguna fila es una medición en una SLM física, y un método que gana aquí puede perder en un dispositivo que el modelo no describe.',
    },
    {
      en: tuned.length ? `Only the methods that declare a tuning grid have tuned rows (${tuned.join(', ')} in this document), so a tuned view compares those methods at their best grid point with the others at their labelled default; it is not a comparison of every family at its optimum.` : 'This document holds no tuned row, so every comparison is between default parameters.',
      es: tuned.length ? `Solo los métodos que declaran una rejilla de ajuste tienen filas ajustadas (${tuned.join(', ')} en este documento), de modo que una vista ajustada compara esos métodos en su mejor punto de la rejilla con los demás en su valor por defecto rotulado; no es una comparación de cada familia en su óptimo.` : 'Este documento no trae filas ajustadas, así que toda comparación es entre parámetros por defecto.',
    },
    {
      en: `${skipped} cells were not run because a method does not accept the target or the dimension; they are listed, not zero, and a tier summary that skips them compares fewer methods on those geometries.`,
      es: `${skipped} celdas no se corrieron porque un método no acepta el objetivo o la dimensión; están listadas, no son cero, y un resumen por nivel que las omite compara menos métodos en esas geometrías.`,
    },
    {
      en: 'The quantities of BS-1, BS-2 and BS-4 that the matrix cannot reproduce are recorded values of the acceptance tests, labelled as such; BS-3 is refuted and BS-4 does not extend to pointing errors. The learned models are judged on generated held-out volumes and geometries, not on experimental data, against a baseline given the same wall-clock.',
      es: 'Las cantidades de BS-1, BS-2 y BS-4 que la matriz no puede reproducir son valores registrados de las pruebas de aceptación, rotulados como tales; BS-3 está refutada y BS-4 no se extiende a errores de puntería. Los modelos aprendidos se juzgan sobre volúmenes y geometrías reservados generados, no sobre datos experimentales, contra una línea base con el mismo reloj.',
    },
  ];
  return (
    <Callout variant="honest" title={es ? 'Lo que esta comparación no dice' : 'What this comparison does not say'}>
      <ul>
        {items.map((it) => (
          <li key={it.en}>{es ? it.es : it.en}</li>
        ))}
      </ul>
    </Callout>
  );
}

export function CaveatTopic() {
  const { data } = useBench();
  return (
    <DocSection title={{ en: 'Limits of the comparison', es: 'Límites de la comparación' }} id="caveat" area="caveat" noRefsReason={{ en: 'the limits restate the protocol and the document, not a paper', es: 'los límites repiten el protocolo y el documento, no un artículo' }}>
      <P
        en="A benchmark is as honest as its stated limits. This one measures the methods of the ladder under one protocol, on synthetic geometries, with a device model, on one machine, and the page reads what that protocol wrote; everything below is what that does not support. A reader who takes a ranking from this page to a physical system should treat it as the ordering that the model predicts, to be confirmed on the hardware, with the quartiles of the table read against any gap that looks decisive."
        es="Un benchmark es tan honesto como sus límites declarados. Este mide los métodos de la escalera bajo un protocolo, en geometrías sintéticas, con un modelo de dispositivo, en una máquina, y la página lee lo que ese protocolo escribió; todo lo que sigue es lo que eso no sustenta. Un lector que lleve una clasificación de esta página a un sistema físico debe tratarla como el orden que predice el modelo, por confirmar en el equipo, leyendo los cuartiles de la tabla frente a cualquier diferencia que parezca decisiva."
      />
      <Note ids={['benchmark-results', 'model-metrics']} />
      <Ready a={data.results}>{(res) => <Limits res={res} />}</Ready>
    </DocSection>
  );
}
