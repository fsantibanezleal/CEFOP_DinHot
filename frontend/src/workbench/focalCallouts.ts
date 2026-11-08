// The three callouts of the focal plane (ADR-0082 rule 5), each anchored on its mark in the picture: the selected trap's intensity against
// its target (the mean), the power left in the zero order, and the relative spread of the traps, pinned to the worst trap. Computed from the
// selection's own result, never typed; a quantity the result does not hold is not drawn.
import { formatNumber, type SceneCalloutDef } from '@fasl-work/caos-app-shell';
import { CALLOUT_BAND, mapAnchor } from './CalloutScene';
import { trapDeviation, type Selection } from './model';
import { umToPixel } from './traps';

type Lang = 'en' | 'es';

export function focalCallouts(sel: Selection, lang: Lang, geom: { width: number; height: number; band: number } = { width: 600, height: 500, band: CALLOUT_BAND }): SceneCalloutDef[] {
  const focal = sel.maps?.focal;
  const res = sel.result;
  if (!focal || !res) return [];
  const f = (v: number, d: number) => formatNumber(v, lang, { decimals: d });
  const at = (x: number, y: number) => {
    const [c, r] = umToPixel(x, y, focal.size, focal.binUm);
    return mapAnchor(c, r, focal.size, focal.size, geom.width, geom.height, geom.band);
  };
  const out: SceneCalloutDef[] = [];
  const idx = sel.traps.findIndex((t) => t.id === sel.trapId);
  const trapI = res.trapI;
  if (idx >= 0 && trapI && trapI[idx] !== undefined) {
    const v = trapI[idx];
    const band = sel.bandPct / 100;
    const t = sel.traps[idx];
    out.push({
      id: 'trap',
      eyebrow: { en: `TRAP ${t.id}`, es: `TRAMPA ${t.id}` },
      value: f(v, 3),
      unit: { en: 'of mean', es: 'de la media' },
      state: Math.abs(v - 1) <= band ? 'normal' : Math.abs(v - 1) <= 2 * band ? 'warning' : 'alarm',
      anchor: at(t.x_um, t.y_um),
      source: { en: 'Selected trap against its target, 1.000', es: 'Trampa elegida frente a su objetivo, 1,000' },
    });
  }
  if (res.metrics) {
    const z = res.metrics.zeroOrder;
    out.push({
      id: 'zero',
      eyebrow: { en: 'ZERO ORDER', es: 'ORDEN CERO' },
      value: f(z * 100, 1),
      unit: '%',
      state: z > 0.1 ? 'alarm' : z > 0.03 ? 'warning' : 'normal',
      anchor: at(0, 0),
      source: { en: 'Power left in the undiffracted order', es: 'Potencia que queda en el orden sin difractar' },
    });
  }
  if (trapI && trapI.length > 0 && sel.traps.length === trapI.length) {
    const s = trapDeviation(trapI);
    let worst = 0;
    trapI.forEach((v, i) => {
      if (Math.abs(v - 1) > Math.abs(trapI[worst] - 1)) worst = i;
    });
    const w = sel.traps[worst];
    out.push({
      id: 'spread',
      eyebrow: { en: 'SPREAD', es: 'DISPERSIÓN' },
      value: f(s.rmsPct, 2),
      unit: '% rms',
      state: s.rmsPct > 20 ? 'alarm' : s.rmsPct > 5 ? 'warning' : 'normal',
      anchor: at(w.x_um, w.y_um),
      source: { en: `Worst trap: ${w.id}`, es: `Peor trampa: ${w.id}` },
    });
  }
  return out;
}
