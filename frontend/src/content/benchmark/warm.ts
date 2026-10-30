// The record of the rejected warm-start model (BS-3, catalog row warmstart-model): `data/derived/models/warmstart-model-rejected.json`,
// written by the evaluation stage when a trained model does not meet its criterion. It is not one of the files the site copies to
// `public/data` (the model-metrics document has no entry for a slot without a released model), so the page reads it from the repository
// at build time; a build without the file shows the claim without its numbers and says so. The glob matches nothing when the file is absent.
export interface WarmStat {
  median: number;
  q1: number;
  q3: number;
}
export interface WarmRecord {
  slot: string;
  status: string;
  criterion: string;
  metrics: {
    held_out_n: number;
    iterations_to_1pct: { model: WarmStat; random: WarmStat };
    final_rel_std_pct: { model: WarmStat; random: WarmStat };
  };
  ratio_random_over_model_median_iterations: number;
  iteration_budget: number;
  control_without_the_network?: {
    what: string;
    median_and_q3_iterations: { random_nfix12?: number[]; random_nfix3?: number[]; model_nfix3?: number[] };
    reading: string;
  };
}

const found = import.meta.glob('../../../../data/derived/models/warmstart-model-rejected.json', { eager: true, import: 'default' }) as Record<string, WarmRecord>;
export const WARM: WarmRecord | null = Object.values(found)[0] ?? null;
