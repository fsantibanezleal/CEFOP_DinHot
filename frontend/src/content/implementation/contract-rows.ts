// The twelve rows of the contract catalog as the Implementation page shows them: id, version and producer are the catalog's own
// cells (docs/contracts/catalog.md, table "Contracts"; `contract.test.ts` in this folder reads the catalog and fails when a row
// here drifts from it), and `reader` says who consumes the document, from the code (the consumer-test cell of the catalog names the
// test, this column names the module that reads it at run time).
import type { Text } from '../../lib/contract.types';

export interface ContractRow {
  id: string;
  version: string;
  /** The producer's path, the catalog's `owner` cell. */
  owner: string;
  /** What the document is, in a few words. */
  what: Text;
  /** Who reads it. */
  reader: Text;
}

export const CONTRACT_ROWS: ContractRow[] = [
  {
    id: 'params-record',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/io/contract.py',
    what: { en: 'The case record: setup, device, target, aberration, methods, budget, seed, drivers and expected ranges. Contract 1.', es: 'El registro del caso: montaje, dispositivo, objetivo, aberración, métodos, presupuesto, semilla, simuladores y rangos esperados. Contrato 1.' },
    reader: { en: 'The bake (stages/preprocess.py) and, as the run request, the live engine', es: 'El precálculo (stages/preprocess.py) y, como solicitud de corrida, el motor en vivo' },
  },
  {
    id: 'case-index',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/core/manifest.py',
    what: { en: 'The index of the cases, the default case and, for a refused case, its reason.', es: 'El índice de los casos, el caso por defecto y, para un caso rechazado, su razón.' },
    reader: { en: 'The artifact layer (api/artifacts.ts) and copy-data.mjs', es: 'La capa de artefactos (api/artifacts.ts) y copy-data.mjs' },
  },
  {
    id: 'case-manifest',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/core/manifest.py',
    what: { en: 'One per case: parameters, seed, engine version, lane verdict, verdict per method, expected ranges, models behind it.', es: 'Uno por caso: parámetros, semilla, versión del motor, veredicto de carril, veredicto por método, rangos esperados, modelos detrás.' },
    reader: { en: 'The artifact layer and the workbench', es: 'La capa de artefactos y la mesa de trabajo' },
  },
  {
    id: 'trace',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/core/trace.py',
    what: { en: 'One per case, at most 256 KiB: metric series per method, the reference method\'s phase mask and focal map, axial cut, feedback, dynamics and rearrangement.', es: 'Una por caso, de 256 KiB como máximo: series de métricas por método, la máscara de fase y el mapa focal del método de referencia, corte axial, realimentación, dinámica y reordenamiento.' },
    reader: { en: 'The workbench views in the replay lane', es: 'Las vistas de la mesa de trabajo en el carril de reproducción' },
  },
  {
    id: 'benchmark-results',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/stages/benchmark.py',
    what: { en: 'The benchmark table (method by geometry by budget), the Pareto fronts and the skipped cells.', es: 'La tabla del benchmark (método por geometría por presupuesto), los frentes de Pareto y las celdas omitidas.' },
    reader: { en: 'The Benchmark page and the Pareto view', es: 'La página Benchmark y la vista de Pareto' },
  },
  {
    id: 'cgh-net',
    version: '1.0.1',
    owner: 'data-pipeline/pipeline/stages/train.py',
    what: { en: 'The model slot target amplitude to phase mask: a card and an ONNX graph. The volumetric GS (M19) at 30 iterations is its baseline.', es: 'El espacio de modelo amplitud objetivo a máscara de fase: una ficha y un grafo ONNX. El GS volumétrico (M19) a 30 iteraciones es su línea base.' },
    reader: { en: 'lib/ort.ts, in the browser', es: 'lib/ort.ts, en el navegador' },
  },
  {
    id: 'warmstart-model',
    version: '1.0.1',
    owner: 'data-pipeline/pipeline/stages/train.py',
    what: { en: 'The model slot trap list to trap phases: a card and an ONNX graph. The random trap phases of the portable RNG are its baseline.', es: 'El espacio de modelo lista de trampas a fases de trampas: una ficha y un grafo ONNX. Las fases aleatorias de las trampas del RNG portable son su línea base.' },
    reader: { en: 'lib/ort.ts, in the browser; its phases start the live M07 run', es: 'lib/ort.ts, en el navegador; sus fases inician la corrida en vivo de M07' },
  },
  {
    id: 'model-metrics',
    version: '1.0.1',
    owner: 'data-pipeline/pipeline/stages/evaluate.py',
    what: { en: 'The held-out metrics of the two model slots against their baselines.', es: 'Las métricas con datos reservados de los dos espacios de modelo frente a sus líneas base.' },
    reader: { en: 'The Benchmark page', es: 'La página Benchmark' },
  },
  {
    id: 'model-evidence',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/stages/train.py',
    what: { en: 'The evidence behind model-metrics: the training records, the rejected candidates and the evaluation detail of the model slots.', es: 'La evidencia detrás de model-metrics: los registros de entrenamiento, los candidatos rechazados y el detalle de la evaluación de los espacios de modelo.' },
    reader: { en: 'The Benchmark page and the tests of the learned methods (tests/learned/)', es: 'La página Benchmark y las pruebas de los métodos aprendidos (tests/learned/)' },
  },
  {
    id: 'engine-reference',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/stages/engine_reference.py',
    what: { en: 'The reference values of the Python engine, written to tests/fixtures/engine/ (a test input, never a run-time document).', es: 'Los valores de referencia del motor en Python, escritos en tests/fixtures/engine/ (una entrada de pruebas, nunca un documento de tiempo de ejecución).' },
    reader: { en: 'The TypeScript parity tests (engine/holo/*.parity.test.ts)', es: 'Las pruebas de paridad en TypeScript (engine/holo/*.parity.test.ts)' },
  },
  {
    id: 'readiness',
    version: '1.0.0',
    owner: 'data-pipeline/pipeline/core/readiness.py',
    what: { en: 'What is real in a build, row by row, in one of six declared states.', es: 'Qué es real en una versión, fila por fila, en uno de seis estados declarados.' },
    reader: { en: 'The artifact layer, the workbench notes and the table below', es: 'La capa de artefactos, las notas de la mesa de trabajo y la tabla de más abajo' },
  },
  {
    id: 'api',
    version: '1.0.0',
    owner: 'app/',
    what: { en: 'The dormant read-only API (GET only); a missing document answers 503 with its declared state.', es: 'La API inactiva de sólo lectura (sólo GET); un documento ausente responde 503 con su estado declarado.' },
    reader: { en: 'Nothing at run time; the site reads the committed documents', es: 'Nadie en tiempo de ejecución; el sitio lee los documentos versionados' },
  },
];
