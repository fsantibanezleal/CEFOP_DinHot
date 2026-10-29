// Group 1, Hologram: what the SLM shows (V1), what its imperfections cost (V7) and the wavefront it is asked to cancel (V8).
// The phase mask is the colormap of a cyclic perceptually uniform map (CET-C1) drawn into a Stage texture; the device stages are
// the engine's (quantize, response curve, crosstalk blur) computed here from the phase so that moving the stage control is live.
import { BarChart, ChipGroup, Knob, PlotCard, SubTabs, Verdict, ViewsRow } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo, useState } from 'react';
import { INTENSITY_LUT, PHASE_LUT } from './colormaps';
import { apertureEnvelopeAtEdge, fillFactorEfficiency, gratingPeriodPx, levelOf, phaseDifference, quantizationEfficiency, stagePhase, TWO_PI } from './decode';
import { Heatmap } from './HeatmapStage';
import { LOADING, Fill, Pending, useActions, useFmt, useStateKey, useT } from './ui';
import { useSelection, type Selection } from './model';
import { coeffArray, J_MAX, MARECHAL_RMS_WAVES, rmsWaves, strehl, wavefrontWaves, zernikeName } from './zernike';

/** The lane and provenance every card of the group declares, from what the selection's maps came from. */
export function cardOf(sel: Selection) {
  return { lane: sel.maps?.lane ?? ('replay' as const), provenance: sel.data.manifest.real_or_synthetic };
}

export function HologramGroup() {
  const { t } = useT();
  const sel = useSelection();
  return (
    <SubTabs
      ariaLabel={t('Hologram views', 'Vistas del holograma')}
      tabs={[
        { id: 'mask', label: t('Phase mask', 'Máscara de fase'), content: sel ? <PhaseMaskView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'device', label: t('Device effects', 'Efectos del dispositivo'), content: sel ? <DeviceEffectsView sel={sel} /> : <Pending label={LOADING} /> },
        { id: 'aberrations', label: t('Aberrations', 'Aberraciones'), content: sel ? <AberrationView sel={sel} /> : <Pending label={LOADING} /> },
      ]}
    />
  );
}

export function PhaseMaskView({ sel }: { sel: Selection }) {
  const { t, pick } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const [cursor, setCursor] = useState<{ col: number; row: number } | null>(null);
  const [region, setRegion] = useState<{ c0: number; r0: number; c1: number; r1: number } | null>(null);
  const maps = sel.maps;
  const n = maps?.nPix ?? 0;
  const shown = useMemo(() => (maps ? stagePhase(maps.phase, n, sel.data.manifest.params.device, sel.stage) : null), [maps, n, sel.data.manifest.params.device, sel.stage]);
  const row = cursor?.row ?? Math.floor(n / 2);
  // Arrays kept between renders: a new array every render (a run reports its progress many times a second) would reset the chart's zoom.
  const xs = useMemo(() => Array.from({ length: n }, (_, i) => i), [n]);
  const idealLine = useMemo(() => (maps ? Array.from({ length: n }, (_, c) => maps.phase[row * n + c]) : []), [maps, n, row]);
  const stageLine = useMemo(() => (shown ? Array.from({ length: n }, (_, c) => shown[row * n + c]) : []), [shown, n, row]);
  if (!maps || !shown) return <Pending label={LOADING} />;
  const bits = sel.data.manifest.params.device?.bit_depth ?? null;
  const centre = region ? { col: Math.floor((region.c0 + region.c1) / 2), row: Math.floor((region.r0 + region.r1) / 2) } : null;
  const period = centre ? gratingPeriodPx(shown, n, centre.row, centre.col) : null;
  const pitch = sel.data.manifest.params.setup.pitch_um;
  const note = region
    ? {
        en: `Region ${region.c1 - region.c0 + 1} x ${region.r1 - region.r0 + 1} pixels: local grating period ${period === null || !Number.isFinite(period) ? 'none (flat)' : `${fmt(period, { decimals: 1 })} px = ${fmt(period * pitch, { decimals: 1 })} um`}.`,
        es: `Región de ${region.c1 - region.c0 + 1} x ${region.r1 - region.r0 + 1} píxeles: período local de la red ${period === null || !Number.isFinite(period) ? 'ninguno (plano)' : `${fmt(period, { decimals: 1 })} px = ${fmt(period * pitch, { decimals: 1 })} um`}.`,
      }
    : {
        en: 'Drag a box on the mask to read its local grating period; hover for a pixel, its phase and its level.',
        es: 'Arrastre un recuadro sobre la máscara para leer su período local; pase el puntero para un píxel, su fase y su nivel.',
      };
  const c = cardOf(sel);
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard fill title={{ en: 'SLM phase mask', es: 'Máscara de fase del SLM' }} {...c} dataKey={stateKey} note={note}>
        <Fill>
          <Heatmap
            label={{ en: 'Phase mask in radians, cyclic colormap', es: 'Máscara de fase en radianes, mapa de color cíclico' }}
            data={shown}
            cols={n}
            rows={n}
            lut={PHASE_LUT}
            range={[0, TWO_PI]}
            region={region}
            onBrush={(c0, r0, c1, r1) => setRegion({ c0, r0, c1, r1 })}
            onPick={() => setRegion(null)}
            onCursor={setCursor}
            describe={(col, rw, v) =>
              pick({
                en: `pixel (${col}, ${rw}): ${fmt(v, { decimals: 3 })} rad${bits !== null && sel.stage !== 'ideal' ? `, level ${levelOf(v, bits)} of ${2 ** bits}` : ''}`,
                es: `píxel (${col}, ${rw}): ${fmt(v, { decimals: 3 })} rad${bits !== null && sel.stage !== 'ideal' ? `, nivel ${levelOf(v, bits)} de ${2 ** bits}` : ''}`,
              })
            }
            summary={t(
              `Phase mask of ${n} by ${n} pixels, ${sel.stage} stage, from 0 to 2 pi radians on a cyclic colormap (0 and 2 pi are the same colour).`,
              `Máscara de fase de ${n} por ${n} píxeles, etapa ${sel.stage === 'ideal' ? 'ideal' : sel.stage === 'quantized' ? 'cuantizada' : 'con diafonía'}, de 0 a 2 pi radianes en un mapa de color cíclico (0 y 2 pi son el mismo color).`,
            )}
          />
        </Fill>
      </PlotCard>
      <PlotCard fill title={{ en: 'Phase along the row under the crosshair', es: 'Fase a lo largo de la fila bajo la cruz' }} {...c} dataKey={stateKey}>
        <Fill quiet>
          <UPlotChart
            height="fill"
            title={{ en: `Phase along pixel row ${row}`, es: `Fase a lo largo de la fila de píxeles ${row}` }}
            x={{ values: xs, label: { en: 'Pixel column', es: 'Columna de píxeles' }, format: { decimals: 0 } }}
            y={{ label: { en: 'Phase', es: 'Fase' }, unit: 'rad', range: [0, TWO_PI] }}
            series={[
              { label: { en: 'Ideal', es: 'Ideal' }, values: idealLine, color: '--color-accent', width: 1.5 },
              ...(sel.stage !== 'ideal' ? [{ label: { en: sel.stage === 'quantized' ? 'Quantized' : 'With crosstalk', es: sel.stage === 'quantized' ? 'Cuantizada' : 'Con diafonía' }, values: stageLine, color: '--color-warn' as const, width: 1.5 }] : []),
            ]}
          />
        </Fill>
      </PlotCard>
    </ViewsRow>
  );
}

/** The three effects of the closed form at an ideal SLM: nothing is lost, every factor is 1. */
const IDEAL_FACTORS = [
  { id: 'quant', label: { en: 'Quantization (none)', es: 'Cuantización (ninguna)' }, value: 1 },
  { id: 'fill', label: { en: 'Fill factor 1', es: 'Factor de llenado 1' }, value: 1 },
  { id: 'edge', label: { en: 'Pixel aperture at the window edge', es: 'Apertura del píxel en el borde de la ventana' }, value: 1 },
];

export function DeviceEffectsView({ sel }: { sel: Selection }) {
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const maps = sel.maps;
  const dev = sel.deviceModel;
  const n = maps?.nPix ?? 0;
  const err = useMemo(() => (maps && dev ? phaseDifference(maps.phase, stagePhase(maps.phase, n, dev, 'crosstalk')) : null), [maps, dev, n]);
  const abs = useMemo(() => (err ? Float32Array.from(err, Math.abs) : null), [err]);
  if (!maps) return <Pending label={LOADING} />;
  const c = cardOf(sel);
  const factors = dev
    ? [
        { id: 'quant', label: { en: dev.bit_depth !== null ? `${dev.bit_depth}-bit quantization` : 'Quantization (none)', es: dev.bit_depth !== null ? `Cuantización de ${dev.bit_depth} bits` : 'Cuantización (ninguna)' }, value: dev.bit_depth !== null ? quantizationEfficiency(2 ** dev.bit_depth) : 1 },
        { id: 'fill', label: { en: `Fill factor ${fmt(dev.fill_factor, { decimals: 2 })}`, es: `Factor de llenado ${fmt(dev.fill_factor, { decimals: 2 })}` }, value: fillFactorEfficiency(dev.fill_factor) },
        { id: 'edge', label: { en: 'Pixel aperture at the window edge', es: 'Apertura del píxel en el borde de la ventana' }, value: apertureEnvelopeAtEdge(dev.fill_factor) },
      ]
    : [];
  const bars = (
    <BarChart
      height="fill"
      title={{ en: 'Efficiency factor of each device effect', es: 'Factor de eficiencia de cada efecto del dispositivo' }}
      axis={{ label: { en: 'Fraction of the ideal light', es: 'Fracción de la luz ideal' }, format: { decimals: 3 }, range: [0, 1] }}
      data={(dev ? factors : IDEAL_FACTORS).map((f) => ({ id: f.id, label: f.label, value: f.value, tone: f.value > 0.9 ? ('good' as const) : f.value > 0.7 ? ('warn' as const) : ('bad' as const) }))}
    />
  );
  // An ideal SLM adds no phase error: there is no map to draw, so the closed-form factors (all 1) take the whole view.
  if (!abs) {
    return (
      <PlotCard
        fill
        title={{ en: 'What each device effect costs, in closed form', es: 'Lo que cuesta cada efecto del dispositivo, en forma cerrada' }}
        {...c}
        dataKey={stateKey}
        note={{ en: 'This run uses an ideal SLM: no phase error to map, and every factor is 1. Pick the case device in the rail if the case has one.', es: 'Esta corrida usa un SLM ideal: no hay error de fase que mapear y todos los factores valen 1. Elija el dispositivo del caso en el panel si lo tiene.' }}
      >
        <Fill>{bars}</Fill>
      </PlotCard>
    );
  }
  return (
    <ViewsRow shares={[2, 3]}>
      <PlotCard
        fill
        title={{ en: 'Phase the device adds', es: 'Fase que añade el dispositivo' }}
        {...c}
        dataKey={stateKey}
        note={{ en: 'Absolute difference between the ideal phase and what the device shows (quantized, response curve, crosstalk), in radians.', es: 'Diferencia absoluta entre la fase ideal y la que muestra el dispositivo (cuantizada, curva de respuesta, diafonía), en radianes.' }}
      >
        <Fill>
          <Heatmap
            label={{ en: 'Absolute phase error of the device, in radians', es: 'Error de fase absoluto del dispositivo, en radianes' }}
            data={abs}
            cols={n}
            rows={n}
            lut={INTENSITY_LUT}
            range={[0, Math.PI]}
            describe={(col, row, v) => t(`pixel (${col}, ${row}): ${fmt(v, { decimals: 3 })} rad`, `píxel (${col}, ${row}): ${fmt(v, { decimals: 3 })} rad`)}
            summary={t(`Absolute phase error map, ${n} by ${n} pixels, mean ${fmt(abs.reduce((a, v) => a + v, 0) / abs.length, { decimals: 3 })} rad.`, `Mapa del error de fase absoluto, ${n} por ${n} píxeles, media ${fmt(abs.reduce((a, v) => a + v, 0) / abs.length, { decimals: 3 })} rad.`)}
          />
        </Fill>
      </PlotCard>
      <PlotCard fill title={{ en: 'What each effect costs, in closed form', es: 'Lo que cuesta cada efecto, en forma cerrada' }} {...c} dataKey={stateKey}>
        <Fill quiet>{bars}</Fill>
      </PlotCard>
    </ViewsRow>
  );
}

export function AberrationView({ sel }: { sel: Selection }) {
  const { t, pick, lang } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const c = cardOf(sel);
  const coeffs = sel.aberration;
  const rms = rmsWaves(coeffs);
  const S = strehl(coeffs);
  const wave = useMemo(() => wavefrontWaves(coeffs, 64), [coeffs]);
  const span = useMemo(() => {
    let lo = Infinity;
    let hi = -Infinity;
    for (const v of wave) if (!Number.isNaN(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    return Number.isFinite(lo) && hi > lo ? ([lo, hi] as [number, number]) : ([-0.01, 0.01] as [number, number]);
  }, [wave]);
  const modes = Array.from({ length: J_MAX - 1 }, (_, i) => i + 2);
  return (
    <>
      <ViewsRow shares={[3, 2]}>
        <PlotCard fill title={{ en: 'Zernike coefficients', es: 'Coeficientes de Zernike' }} {...c} dataKey={stateKey}>
          <Fill>
            <div className="dh-stack">
            <div className="dh-controls">
              <ChipGroup
                id="correction"
                label={{ en: 'Aberration', es: 'Aberración' }}
                value={sel.corrected ? 'on' : 'off'}
                onChange={(v) => act.setCorrected(v === 'on')}
                options={[
                  { id: 'off', label: { en: 'As the case', es: 'Del caso' } },
                  { id: 'on', label: { en: 'Corrected', es: 'Corregida' }, hint: { en: 'Remove the case aberration before your edits.', es: 'Quita la aberración del caso antes de sus ediciones.' } },
                ]}
              />
              <Knob
                id="zmode"
                label={{ en: 'Zernike mode', es: 'Modo de Zernike' }}
                hint={{ en: `Noll index ${sel.zmode}: ${zernikeName(sel.zmode).en}.`, es: `Índice de Noll ${sel.zmode}: ${zernikeName(sel.zmode).es}.` }}
                value={sel.zmode}
                min={2}
                max={J_MAX}
                step={1}
                unit={{ en: 'Noll index', es: 'índice de Noll' }}
                format={{ decimals: 0 }}
                onChange={(v) => act.selectMode(Math.round(v))}
              />
              <Knob
                id="zcoeff"
                label={{ en: 'Mode coefficient', es: 'Coeficiente del modo' }}
                hint={{ en: 'The coefficient of the selected mode, in waves; the wavefront, the rms and the Strehl follow.', es: 'El coeficiente del modo elegido, en ondas; el frente de onda, el rms y el Strehl lo siguen.' }}
                value={coeffs[sel.zmode - 1] ?? 0}
                min={-0.5}
                max={0.5}
                step={0.005}
                unit={{ en: 'waves', es: 'ondas' }}
                format={{ decimals: 3 }}
                onChange={(v) => act.setCoeff(sel.zmode, v)}
              />
            </div>
              <div className="dh-fill">
            <BarChart
              height="fill"
              orientation="vertical"
              values={false}
              title={{ en: 'Zernike coefficient by Noll index', es: 'Coeficiente de Zernike por índice de Noll' }}
              axis={{ label: { en: 'Coefficient', es: 'Coeficiente' }, unit: { en: 'waves', es: 'ondas' }, format: { decimals: 3 } }}
              data={modes.map((j) => ({
                id: String(j),
                label: { en: `${j}`, es: `${j}` },
                hint: zernikeName(j),
                value: coeffs[j - 1],
                tone: j === sel.zmode ? ('accent' as const) : coeffs[j - 1] === 0 ? ('neutral' as const) : ('warn' as const),
                highlight: j === sel.zmode,
              }))}
            />
              </div>
            </div>
          </Fill>
        </PlotCard>
        <PlotCard
          fill
          title={{ en: 'Wavefront over the pupil', es: 'Frente de onda sobre la pupila' }}
          {...c}
          dataKey={stateKey}
        >
          <Fill quiet>
            <div className="dh-stack">
              <Verdict
                compact
                title={{ en: 'Strehl ratio (Marechal)', es: 'Razón de Strehl (Maréchal)' }}
                tone={rms <= MARECHAL_RMS_WAVES ? 'good' : rms <= 2 * MARECHAL_RMS_WAVES ? 'warn' : 'bad'}
                verdict={{
                  en: `rms ${fmt(rms, { decimals: 3 })} waves, Strehl ${fmt(S, { decimals: 3 })}: ${rms <= MARECHAL_RMS_WAVES ? 'inside' : 'beyond'} the Marechal limit of 1/14 wave.`,
                  es: `rms ${fmt(rms, { decimals: 3 })} ondas, Strehl ${fmt(S, { decimals: 3 })}: ${rms <= MARECHAL_RMS_WAVES ? 'dentro' : 'más allá'} del límite de Maréchal de 1/14 de onda.`,
                }}
              />
              <div className="dh-fill">
            <Heatmap
              label={{ en: 'Wavefront in waves over the SLM pupil', es: 'Frente de onda en ondas sobre la pupila del SLM' }}
              data={wave}
              cols={64}
              rows={64}
              lut={INTENSITY_LUT}
              range={span}
              describe={(col, row, v) => pick({ en: `pupil (${col}, ${row}): ${fmt(v, { decimals: 4 })} waves`, es: `pupila (${col}, ${row}): ${fmt(v, { decimals: 4 })} ondas` })}
              summary={t(`Wavefront of ${coeffs.filter((x) => x !== 0).length} active modes, rms ${fmt(rms, { decimals: 3 })} waves, from ${fmt(span[0], { decimals: 3 })} to ${fmt(span[1], { decimals: 3 })} waves.`, `Frente de onda de ${coeffs.filter((x) => x !== 0).length} modos activos, rms ${fmt(rms, { decimals: 3 })} ondas, de ${fmt(span[0], { decimals: 3 })} a ${fmt(span[1], { decimals: 3 })} ondas.`)}
              tableLabel={{ en: `Wavefront values (${lang})`, es: 'Valores del frente de onda' }}
            />
              </div>
            </div>
          </Fill>
        </PlotCard>
      </ViewsRow>
    </>
  );
}

export { coeffArray };
