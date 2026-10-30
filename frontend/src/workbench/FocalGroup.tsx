// Group 2, Focal plane: where the light goes (V2, with the zero order, the replica boundary and the trap editor), how tall a trap is
// along z (V5, the xz and yz cuts) and, on three-dimensional cases, the focal volume the engine computes (V6).
// The trap editor is a mode of the map (inspect, add, move, delete): the map is the surface the traps live on.
import { ChipGroup, PlotCard, SubTabs, ViewsRow } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { rayleighUm } from '../lib/ort';
import { INTENSITY_LUT } from './colormaps';
import { cutRequest, type Plane } from './cuts';
import { getEngine } from './engine';
import { Heatmap, type HeatMark, type HeatRect } from './HeatmapStage';
import { cardOf } from './HologramGroup';
import { is3D, isShaped, useSelection, type Axial, type Selection } from './model';
import { pixelToUm, umToPixel } from './traps';
import { Fill, LOADING, Pending, Unavailable, useActions, useFmt, useStateKey, useT } from './ui';

const Lobes3D = lazy(() => import('./Lobes3D').then((m) => ({ default: m.Lobes3D })));
const Volume3D = lazy(() => import('./Volume3D').then((m) => ({ default: m.Volume3D })));

export function FocalGroup() {
  const { t } = useT();
  const sel = useSelection();
  const tabs = [
    { id: 'plane', label: t('Focal plane', 'Plano focal'), content: sel ? <FocalPlaneView sel={sel} /> : <Pending label={LOADING} /> },
    { id: 'cuts', label: t('Axial cut', 'Corte axial'), content: sel ? <AxialView sel={sel} /> : <Pending label={LOADING} /> },
    ...(sel && is3D(sel.traps)
      ? [
          sel.engineAvailable
            ? { id: 'volume', label: t('3D volume', 'Volumen 3D'), content: <Suspense fallback={<Pending label={LOADING} />}><Volume3D sel={sel} /></Suspense> }
            : { id: 'lobes', label: t('3D lobes', 'Lóbulos 3D'), content: <Suspense fallback={<Pending label={LOADING} />}><Lobes3D sel={sel} /></Suspense> },
        ]
      : []),
  ];
  return <SubTabs ariaLabel={t('Focal plane views', 'Vistas del plano focal')} tabs={tabs} />;
}

export function FocalPlaneView({ sel }: { sel: Selection }) {
  const { t, pick } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const maps = sel.maps;
  const focal = maps?.focal ?? null;
  const c = cardOf(sel);
  const size = focal?.size ?? 0;
  const bin = focal?.binUm ?? 1;
  const centre = Math.floor(size / 2);

  const marks: HeatMark[] = useMemo(() => {
    if (!focal) return [];
    const out: HeatMark[] = sel.traps.map((tr) => {
      const [col, row] = umToPixel(tr.x_um, tr.y_um, size, bin);
      return { id: tr.id, col, row, kind: 'ring', tone: tr.id === sel.trapId ? 'accent' : 'good', selected: tr.id === sel.trapId, label: sel.traps.length <= 64 ? String(tr.id) : tr.id === sel.trapId ? String(tr.id) : undefined };
    });
    out.push({ col: centre, row: centre, kind: 'cross', tone: 'warn', radius: 8, label: t('zero order', 'orden cero') });
    return out;
  }, [focal, sel.traps, sel.trapId, size, bin, centre, t]);

  const rects: HeatRect[] = useMemo(() => {
    if (!maps || !focal) return [];
    const h = maps.halfFieldUm / bin;
    const inside = centre - h >= 0 && centre + h <= size;
    return inside ? [{ c0: centre - h, r0: centre - h, c1: centre + h, r1: centre + h, tone: 'bad', dashed: true, label: t('replica boundary', 'límite de réplica') }] : [];
  }, [maps, focal, bin, centre, size, t]);

  const region = useMemo(() => {
    if (!sel.region || !focal) return null;
    const [c0, r0] = umToPixel(sel.region.x0, sel.region.y0, size, bin);
    const [c1, r1] = umToPixel(sel.region.x1, sel.region.y1, size, bin);
    return { c0, r0, c1, r1 };
  }, [sel.region, focal, size, bin]);

  const trap = sel.traps.find((x) => x.id === sel.trapId) ?? sel.traps[0] ?? null;
  // A trap target is read through its selected trap; a shaped target has none, so the profiles go through the centre of the field.
  const through = trap ? { x: trap.x_um, y: trap.y_um, id: trap.id } : focal && isShaped(sel.data.manifest) ? { x: 0, y: 0, id: null } : null;
  const profile = useMemo(() => {
    if (!focal || !through) return null;
    const [col, row] = umToPixel(through.x, through.y, size, bin);
    if (col < 0 || col >= size || row < 0 || row >= size) return null;
    const xs = Array.from({ length: size }, (_, i) => (i - centre) * bin);
    return { xs, alongX: xs.map((_, i) => focal.db[row * size + i]), alongY: xs.map((_, i) => focal.db[i * size + col]) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focal, through?.x, through?.y, size, bin, centre]);

  if (!maps) return <Pending label={LOADING} />;
  const range: [number, number] = [sel.dbFloor, 0];
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Focal-plane intensity', es: 'Intensidad en el plano focal' }}
        {...c}
        dataKey={stateKey}
        note={{
          en: 'dB against the mean trap, y increases downward as in the engine. Click a trap to select it; drag a box to select a region; the editor modes in the rail add, move or delete traps.',
          es: 'dB respecto de la trampa media; y aumenta hacia abajo, como en el motor. Pulse una trampa para elegirla; arrastre un recuadro para elegir una región; los modos del editor en el panel agregan, mueven o borran trampas.',
        }}
      >
        <Fill>
          {act.editError && (
            <p className="dh-alert" role="alert" data-editor-error="">
              {pick(act.editError)}
            </p>
          )}
          {focal ? (
            <Heatmap
              label={{ en: 'Focal-plane intensity in dB with trap markers', es: 'Intensidad del plano focal en dB con marcas de trampas' }}
              data={focal.db}
              cols={size}
              rows={size}
              lut={INTENSITY_LUT}
              range={range}
              marks={marks}
              rects={rects}
              region={region}
              mode={act.mode}
              onPick={(col, row) => {
                let best: number | null = null;
                let bd = 4;
                for (const tr of sel.traps) {
                  const [tc, tr2] = umToPixel(tr.x_um, tr.y_um, size, bin);
                  const d = Math.hypot(tc - col, tr2 - row);
                  if (d <= bd) {
                    bd = d;
                    best = tr.id;
                  }
                }
                act.selectTrap(best);
                if (best === null) act.setRegion(null);
              }}
              onBrush={(c0, r0, c1, r1) => {
                const [x0, y0] = pixelToUm(c0, r0, size, bin);
                const [x1, y1] = pixelToUm(c1, r1, size, bin);
                act.setRegion({ x0, y0, x1, y1 });
              }}
              onAdd={(col, row) => act.addTrap(...pixelToUm(col, row, size, bin))}
              onMove={(id, col, row) => act.moveTrap(id, ...pixelToUm(col, row, size, bin))}
              onDelete={(id) => act.deleteTrap(id)}
              describe={(col, row, v) => {
                const [x, y] = pixelToUm(col, row, size, bin);
                return pick({ en: `x ${fmt(x, { decimals: 2 })} um, y ${fmt(y, { decimals: 2 })} um: ${fmt(v, { decimals: 1 })} dB`, es: `x ${fmt(x, { decimals: 2 })} um, y ${fmt(y, { decimals: 2 })} um: ${fmt(v, { decimals: 1 })} dB` });
              }}
              summary={t(
                `Focal-plane intensity, ${size} by ${size} bins of ${fmt(bin, { decimals: 2 })} um, ${sel.traps.length} traps marked, colour scale ${fmt(sel.dbFloor, { decimals: 0 })} to 0 dB.`,
                `Intensidad del plano focal, ${size} por ${size} bins de ${fmt(bin, { decimals: 2 })} um, ${sel.traps.length} trampas marcadas, escala de color de ${fmt(sel.dbFloor, { decimals: 0 })} a 0 dB.`,
              )}
            />
          ) : (
            <Unavailable reason={{ en: 'The browser inference of this model returns the SLM phase only; the focal plane of a learned phase comes from the engine, which is not on this build.', es: 'La inferencia en el navegador de este modelo devuelve solo la fase del SLM; el plano focal de una fase aprendida lo calcula el motor, que no está en esta versión.' }} />
          )}
        </Fill>
      </PlotCard>
      <PlotCard fill title={{ en: 'Profiles through the selected trap', es: 'Perfiles por la trampa elegida' }} {...c} dataKey={stateKey}>
        <Fill quiet>
          {profile && through ? (
            <UPlotChart
              height="fill"
              title={through.id === null ? { en: 'Intensity along x and y through the centre of the field', es: 'Intensidad a lo largo de x e y por el centro del campo' } : { en: `Intensity along x and y through trap ${through.id}`, es: `Intensidad a lo largo de x e y por la trampa ${through.id}` }}
              x={{ values: profile.xs, label: { en: 'Offset from the centre', es: 'Distancia al centro' }, unit: 'um', format: { decimals: 1 } }}
              y={{ label: { en: 'Intensity', es: 'Intensidad' }, unit: 'dB', range: [sel.dbFloor, 3] }}
              series={[
                { label: { en: 'Along x', es: 'A lo largo de x' }, values: profile.alongX, color: '--color-accent' },
                { label: { en: 'Along y', es: 'A lo largo de y' }, values: profile.alongY, color: '--color-warn', dash: [5, 4] },
              ]}
              marks={[{ x: 0, label: { en: 'zero order', es: 'orden cero' } }]}
            />
          ) : (
            <Unavailable reason={{ en: 'Select a trap on the map to read its profiles.', es: 'Elija una trampa en el mapa para leer sus perfiles.' }} />
          )}
        </Fill>
      </PlotCard>
    </ViewsRow>
  );
}

/** The cut as the card draws it: dB against the mean trap, clipped to the colour floor. */
function cutDb(xz: Float32Array, floor: number): Float32Array {
  return Float32Array.from(xz, (v) => Math.max(floor, Math.min(0, 10 * Math.log10(Math.max(v, 1e-30)))));
}

export function AxialView({ sel }: { sel: Selection }) {
  const { t, pick } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const maps = sel.maps;
  const c = cardOf(sel);
  const plane = sel.plane;
  const [cut, setCut] = useState<{ axial: Axial; key: string; from: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const trap = sel.traps.find((x) => x.id === sel.trapId) ?? sel.traps[0] ?? null;
  const shaped = sel.data.manifest.params.target.kind !== 'traps';
  // The bake keeps one xz cut, through its own trap; every other cut (the yz plane, another trap, a live hologram) is the engine's.
  const baked = plane === 'xz' && maps?.lane === 'replay' && maps.axial && trap && maps.axial.trapId === trap.id ? maps.axial : null;
  const wanted = `${maps?.method}|${maps?.lane}|${trap?.id}|${plane}|${sel.edited}|${sel.device}|${sel.aberrationEdited}|${sel.coeffKey}|${sel.dbFloor}`;
  const needEngine = !baked && sel.engineAvailable && !!maps && !!trap && !shaped;

  useEffect(() => {
    if (!needEngine || !maps || !trap) return;
    let on = true;
    setError(null);
    void getEngine().then(async (e) => {
      try {
        const phase = sel.device === 'case' && maps.displayed ? maps.displayed : maps.phase;
        const req = cutRequest(plane, phase, maps.nPix, sel.runParams, trap.id, 64);
        const r = await e.client.axialCut(req);
        if (!on) return;
        setCut({ axial: { db: cutDb(r.xz, sel.dbFloor), nx: r.nx, nz: r.nz, zUm: r.zUm, trapId: trap.id }, key: wanted, from: maps.method });
      } catch (err) {
        if (on) setError(String(err));
      }
    });
    return () => {
      on = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, needEngine]);

  if (!maps) return <Pending label={LOADING} />;
  const live = needEngine && cut?.key === wanted ? cut : null;
  const axial = baked ?? live?.axial ?? null;
  const lane: 'live' | 'replay' = live ? 'live' : 'replay';
  const zr = rayleighUm(sel.data.manifest.params.setup);
  const lateral = plane === 'xz' ? 'x' : 'y';
  const rects: HeatRect[] = axial
    ? [-zr, zr]
        .map((z) => ((z - axial.zUm[0]) / (axial.zUm[1] - axial.zUm[0])) * axial.nz)
        .filter((r) => r >= 0 && r <= axial.nz)
        .map((r) => ({ c0: 0, r0: r, c1: axial.nx, r1: r, tone: 'warn' as const, dashed: true, label: 'z_R' }))
    : [];
  const source = live
    ? maps.lane === 'live'
      ? { en: `Computed now in your browser from the live ${maps.method} hologram.`, es: `Calculado ahora en su navegador desde el holograma ${maps.method} en vivo.` }
      : { en: `Computed now in your browser from the baked ${maps.method} hologram (its 8-bit phase).`, es: `Calculado ahora en su navegador desde el holograma ${maps.method} de la generación (su fase de 8 bits).` }
    : axial
      ? { en: `Replayed from the bake: the xz cut of the reference method ${maps.method} through trap ${axial.trapId}.`, es: `Reproducido de la generación: el corte xz del método de referencia ${maps.method} por la trampa ${axial.trapId}.` }
      : { en: '', es: '' };
  return (
    <PlotCard
      fill
      title={{ en: `Axial (${plane}) cut through a trap`, es: `Corte axial (${plane}) por una trampa` }}
      {...c}
      lane={lane}
      dataKey={stateKey}
      note={{
        en: `Intensity in dB, ${lateral} across and z down, dashed lines at plus and minus one Rayleigh range (${fmt(zr, { decimals: 2 })} um). ${source.en}`,
        es: `Intensidad en dB, ${lateral} a lo ancho y z hacia abajo, líneas segmentadas en más y menos un rango de Rayleigh (${fmt(zr, { decimals: 2 })} um). ${source.es}`,
      }}
      actions={
        <ChipGroup
          id="cut-plane"
          label={{ en: 'Plane', es: 'Plano' }}
          value={plane}
          onChange={(v) => act.setPlane(v as Plane)}
          options={[
            { id: 'xz', label: { en: 'xz', es: 'xz' }, hint: { en: 'Across x and down z through the selected trap.', es: 'A lo ancho de x y hacia abajo en z por la trampa elegida.' } },
            { id: 'yz', label: { en: 'yz', es: 'yz' }, hint: { en: 'Across y and down z through the selected trap (computed by the engine).', es: 'A lo ancho de y y hacia abajo en z por la trampa elegida (la calcula el motor).' } },
          ]}
        />
      }
    >
      <Fill>
        {error && <p className="dh-alert" role="alert">{error}</p>}
        {axial ? (
          <Heatmap
            square={false}
            label={{ en: `${plane} cut through trap ${axial.trapId}, intensity in dB`, es: `Corte ${plane} por la trampa ${axial.trapId}, intensidad en dB` }}
            data={axial.db}
            cols={axial.nx}
            rows={axial.nz}
            lut={INTENSITY_LUT}
            range={[sel.dbFloor, 0]}
            rects={rects}
            describe={(col, row, v) => {
              const z = axial.zUm[0] + (row / axial.nz) * (axial.zUm[1] - axial.zUm[0]);
              const x = (col - Math.floor(axial.nx / 2)) * maps.binUm;
              return pick({ en: `${lateral} ${fmt(x, { decimals: 2 })} um, z ${fmt(z, { decimals: 2 })} um: ${fmt(v, { decimals: 1 })} dB`, es: `${lateral} ${fmt(x, { decimals: 2 })} um, z ${fmt(z, { decimals: 2 })} um: ${fmt(v, { decimals: 1 })} dB` });
            }}
            summary={t(`Axial ${plane} cut of trap ${axial.trapId}, ${axial.nx} columns by ${axial.nz} rows, z from ${fmt(axial.zUm[0], { decimals: 2 })} to ${fmt(axial.zUm[1], { decimals: 2 })} um.`, `Corte axial ${plane} de la trampa ${axial.trapId}, ${axial.nx} columnas por ${axial.nz} filas, z de ${fmt(axial.zUm[0], { decimals: 2 })} a ${fmt(axial.zUm[1], { decimals: 2 })} um.`)}
          />
        ) : needEngine && !error ? (
          <Pending label={{ en: 'The engine is computing the cut', es: 'El motor está calculando el corte' }} />
        ) : (
          <Unavailable
            reason={
              shaped
                ? { en: 'A shaped target has no trap to cut through: the axial cut is defined for trap targets.', es: 'Un objetivo con forma no tiene una trampa por la que cortar: el corte axial se define para objetivos con trampas.' }
                : { en: 'This case has no axial cut in the bake for this trap and plane (the bake keeps the xz cut of one trap), and the live engine is not on this build.', es: 'Este caso no tiene corte axial en la generación para esta trampa y plano (la generación guarda el corte xz de una trampa) y el motor en vivo no está en esta versión.' }
            }
          />
        )}
      </Fill>
    </PlotCard>
  );
}
