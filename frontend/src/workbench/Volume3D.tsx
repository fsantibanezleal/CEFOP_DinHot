// V6, the focal volume of a three-dimensional case (C05 and any case whose traps sit in more than one plane): the voxels of the engine's
// axial cuts through every row and column of traps, drawn as a point cloud above a fraction of the peak (volume.ts). The engine computes
// the planes; this view samples the volume with them, so a lobe appears wherever a plane crosses it, and the card says so. The scene
// renders on demand, never in a loop (G8): orbit by dragging or with the arrow keys, zoom with the wheel (focused) or + and -, and
// 0 resets the camera. The threshold is a control of the workbench (it changes the selection key, G9).
import { PlotCard } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useRef, useState } from 'react';
import { cutRequest } from './cuts';
import { INTENSITY_LUT, lutRgb } from './colormaps';
import { getEngine } from './engine';
import { cardOf } from './HologramGroup';
import { type Selection } from './model';
import { Fill, Pending, Unavailable, useActions, useFmt, useStateKey, useT } from './ui';
import { slabPlan, volumeExtent, volumePoints, type Slab } from './volume';

const PLANES_PER_AXIS = 3;
const POINT_CAP = 60000;
const CUT_NZ = 32;

interface Computed {
  key: string;
  slabs: Slab[];
}

/** The slabs of the selection, computed one after the other by the engine; `progress` counts them while the engine works. */
function useSlabs(sel: Selection, active: boolean): { slabs: Slab[] | null; progress: { done: number; total: number } | null; error: string | null } {
  const maps = sel.maps;
  const key = `${maps?.method}|${maps?.lane}|${sel.device}|${sel.edited}|${sel.traps.length}|${sel.aberrationEdited}|${sel.coeffKey}|${sel.traps.map((t) => `${t.x_um},${t.y_um},${t.z_um}`).join(';')}`;
  const [done, setDone] = useState<Computed | null>(null);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!active || !maps || !sel.engineAvailable) return;
    let on = true;
    setError(null);
    setProgress({ done: 0, total: 0 });
    void getEngine().then(async (e) => {
      try {
        const phase = sel.device === 'case' && maps.displayed ? maps.displayed : maps.phase;
        const plan = [
          ...slabPlan(sel.traps, 'xz', PLANES_PER_AXIS).map((p) => ({ ...p, plane: 'xz' as const })),
          ...slabPlan(sel.traps, 'yz', PLANES_PER_AXIS).map((p) => ({ ...p, plane: 'yz' as const })),
        ];
        const slabs: Slab[] = [];
        for (const [i, p] of plan.entries()) {
          setProgress({ done: i, total: plan.length });
          const r = await e.client.axialCut(cutRequest(p.plane, phase, maps.nPix, sel.runParams, p.trapId, CUT_NZ));
          if (!on) return;
          slabs.push({ plane: p.plane, posUm: p.posUm, trapId: p.trapId, lin: r.xz, nx: r.nx, nz: r.nz, zUm: r.zUm, binUm: maps.binUm });
        }
        if (on) {
          setDone({ key, slabs });
          setProgress(null);
        }
      } catch (err) {
        if (on) {
          setError(String(err));
          setProgress(null);
        }
      }
    });
    return () => {
      on = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, active]);
  return { slabs: done?.key === key ? done.slabs : null, progress, error };
}

export function Volume3D({ sel }: { sel: Selection }) {
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const c = cardOf(sel);
  const host = useRef<HTMLDivElement | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const { slabs, progress, error } = useSlabs(sel, !failed);
  const points = useMemo(() => (slabs ? volumePoints(slabs, sel.volThreshold, POINT_CAP) : null), [slabs, sel.volThreshold]);
  const extent = useMemo(() => (slabs ? volumeExtent(sel.traps, slabs) : null), [slabs, sel.traps]);
  const trap = sel.traps.find((x) => x.id === sel.trapId) ?? null;

  useEffect(() => {
    const el = host.current;
    if (!el || !points || !extent) return;
    let disposed = false;
    let cleanup = () => undefined as void;
    void import('three').then((THREE) => {
      if (disposed) return;
      try {
        const css = getComputedStyle(document.documentElement);
        const col = (name: string) => new THREE.Color(css.getPropertyValue(name).trim() || '#888888');
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        const size = () => ({ w: Math.max(el.clientWidth, 200), h: Math.max(el.clientHeight, 160) });
        let { w, h } = size();
        renderer.setSize(w, h, false);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        el.appendChild(renderer.domElement);
        const dom = renderer.domElement;
        dom.setAttribute('data-drawn', 'true');
        // The canvas fills the host without sizing it: the host takes the height the card leaves, so a resize can shrink as well as grow.
        Object.assign(dom.style, { position: 'absolute', left: '0', top: '0', width: '100%', height: '100%', display: 'block' });
        const scene = new THREE.Scene();
        // The scene is in micrometres with the optical axis up: x, z, y of the engine.
        const pos = new Float32Array(points.n * 3);
        const rgb = new Float32Array(points.n * 3);
        for (let k = 0; k < points.n; k++) {
          pos[3 * k] = points.xyz[3 * k];
          pos[3 * k + 1] = points.xyz[3 * k + 2];
          pos[3 * k + 2] = points.xyz[3 * k + 1];
          const [r, g, b] = lutRgb(INTENSITY_LUT, points.u[k]);
          rgb[3 * k] = r / 255;
          rgb[3 * k + 1] = g / 255;
          rgb[3 * k + 2] = b / 255;
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(rgb, 3));
        const mat = new THREE.PointsMaterial({ size: 3, sizeAttenuation: false, vertexColors: true });
        scene.add(new THREE.Points(geo, mat));
        // The box of the drawing and the traps (the selected one in the accent colour), so the cloud has a frame.
        const box = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(2 * extent.x, 2 * extent.z, 2 * extent.y)), new THREE.LineBasicMaterial({ color: col('--color-fg-faint') }));
        scene.add(box);
        const tp = new Float32Array(sel.traps.length * 3);
        sel.traps.forEach((tr, i) => tp.set([tr.x_um, tr.z_um, tr.y_um], 3 * i));
        const tg = new THREE.BufferGeometry();
        tg.setAttribute('position', new THREE.BufferAttribute(tp, 3));
        const tm = new THREE.PointsMaterial({ size: 6, sizeAttenuation: false, color: col('--color-good'), transparent: true, opacity: 0.7 });
        scene.add(new THREE.Points(tg, tm));
        let selGeo: import('three').BufferGeometry | null = null;
        let selMat: import('three').PointsMaterial | null = null;
        if (trap) {
          selGeo = new THREE.BufferGeometry();
          selGeo.setAttribute('position', new THREE.BufferAttribute(Float32Array.of(trap.x_um, trap.z_um, trap.y_um), 3));
          selMat = new THREE.PointsMaterial({ size: 11, sizeAttenuation: false, color: col('--color-accent') });
          scene.add(new THREE.Points(selGeo, selMat));
        }
        const reach = Math.max(extent.x, extent.y, extent.z);
        const camera = new THREE.PerspectiveCamera(40, w / h, reach / 100, reach * 100);
        const home = { az: 0.8, el: 0.5, dist: reach * 3 };
        const state = { ...home };
        const draw = () => {
          camera.position.set(state.dist * Math.cos(state.el) * Math.sin(state.az), state.dist * Math.sin(state.el), state.dist * Math.cos(state.el) * Math.cos(state.az));
          camera.lookAt(0, 0, 0);
          renderer.render(scene, camera);
        };
        draw();
        dom.tabIndex = 0;
        dom.setAttribute('role', 'img');
        dom.setAttribute('aria-label', t('Focal volume sampled by the engine cuts; drag or use the arrow keys to orbit, plus and minus to zoom, 0 to reset', 'Volumen focal muestreado por los cortes del motor; arrastre o use las flechas para orbitar, más y menos para acercar, 0 para reiniciar'));
        let down: { x: number; y: number } | null = null;
        const pd = (e: PointerEvent) => {
          down = { x: e.clientX, y: e.clientY };
          dom.setPointerCapture(e.pointerId);
          dom.focus();
        };
        const pm = (e: PointerEvent) => {
          if (!down) return;
          state.az -= (e.clientX - down.x) * 0.01;
          state.el = Math.max(-1.5, Math.min(1.5, state.el + (e.clientY - down.y) * 0.01));
          down = { x: e.clientX, y: e.clientY };
          draw();
        };
        const pu = () => {
          down = null;
        };
        const wheel = (e: WheelEvent) => {
          if (document.activeElement !== dom && !e.ctrlKey && !e.metaKey) return;
          e.preventDefault();
          state.dist = Math.max(reach * 0.4, Math.min(reach * 20, state.dist * (e.deltaY < 0 ? 0.88 : 1.14)));
          draw();
        };
        const key = (e: KeyboardEvent) => {
          const step = 0.08;
          if (e.key === 'ArrowLeft') state.az -= step;
          else if (e.key === 'ArrowRight') state.az += step;
          else if (e.key === 'ArrowUp') state.el = Math.min(1.5, state.el + step);
          else if (e.key === 'ArrowDown') state.el = Math.max(-1.5, state.el - step);
          else if (e.key === '+' || e.key === '=') state.dist = Math.max(reach * 0.4, state.dist * 0.88);
          else if (e.key === '-') state.dist = Math.min(reach * 20, state.dist * 1.14);
          else if (e.key === '0') Object.assign(state, home);
          else return;
          e.preventDefault();
          draw();
        };
        dom.addEventListener('pointerdown', pd);
        dom.addEventListener('pointermove', pm);
        dom.addEventListener('pointerup', pu);
        dom.addEventListener('wheel', wheel, { passive: false });
        dom.addEventListener('keydown', key);
        // A resize redraws once; nothing renders between events.
        const ro = new ResizeObserver(() => {
          const s = size();
          if (s.w === w && s.h === h) return;
          ({ w, h } = s);
          renderer.setSize(w, h, false);
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          draw();
        });
        ro.observe(el);
        cleanup = () => {
          ro.disconnect();
          dom.removeEventListener('pointerdown', pd);
          dom.removeEventListener('pointermove', pm);
          dom.removeEventListener('pointerup', pu);
          dom.removeEventListener('wheel', wheel);
          dom.removeEventListener('keydown', key);
          for (const g of [geo, tg, selGeo]) g?.dispose();
          for (const m of [mat, tm, selMat]) m?.dispose();
          renderer.dispose();
          renderer.forceContextLoss();
          dom.remove();
        };
      } catch (e) {
        setFailed(String(e));
      }
    });
    return () => {
      disposed = true;
      cleanup();
    };
    // the scene is rebuilt when the points, the frame or the selected trap change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, extent, trap?.id]);

  const lane = slabs ? 'live' : c.lane;
  const from = sel.maps?.lane === 'live' ? t(`the live ${sel.maps.method} hologram`, `el holograma ${sel.maps.method} en vivo`) : t(`the baked ${sel.maps?.method} hologram (its 8-bit phase)`, `el holograma ${sel.maps?.method} de la generación (su fase de 8 bits)`);
  return (
    <PlotCard
      fill
      title={{ en: 'Focal volume in 3D', es: 'Volumen focal en 3D' }}
      {...c}
      lane={lane}
      dataKey={stateKey}
      note={{
        en: `Voxels of the engine's axial cuts through each row and column of traps (at most ${PLANES_PER_AXIS} planes per direction), computed now in your browser from ${from}, drawn above a fraction of the peak. Between the planes nothing is drawn. Green dots are the traps, the accent dot the selected one.`,
        es: `Vóxeles de los cortes axiales del motor por cada fila y columna de trampas (como mucho ${PLANES_PER_AXIS} planos por dirección), calculados ahora en su navegador desde ${from}, dibujados sobre una fracción del pico. Entre los planos no se dibuja nada. Los puntos verdes son las trampas y el de acento la elegida.`,
      }}
    >
      <Fill>
        <div className="dh-stack">
          <div className="dh-scrub">
            <label htmlFor="dh-threshold">{t('Threshold (fraction of the peak)', 'Umbral (fracción del pico)')}</label>
            <input id="dh-threshold" type="range" min={0.05} max={0.95} step={0.05} value={sel.volThreshold} onChange={(e) => act.setVolThreshold(Number(e.target.value))} />
            <output>{fmt(sel.volThreshold, { decimals: 2 })}</output>
            <span role="status">
              {points
                ? t(`${fmt(points.n, { decimals: 0 })} voxels${points.thinned ? ' (thinned to the cap)' : ''} in ${slabs?.length ?? 0} planes.`, `${fmt(points.n, { decimals: 0 })} vóxeles${points.thinned ? ' (reducidos al tope)' : ''} en ${slabs?.length ?? 0} planos.`)
                : progress
                  ? t(`Computing plane ${progress.done + 1} of ${progress.total || '...'}.`, `Calculando el plano ${progress.done + 1} de ${progress.total || '...'}.`)
                  : ''}
            </span>
          </div>
          {failed ? (
            <Unavailable reason={{ en: `The 3D view needs WebGL, which this browser did not give (${failed}).`, es: `La vista 3D necesita WebGL, que este navegador no dio (${failed}).` }} />
          ) : error ? (
            <Unavailable reason={{ en: `The engine could not compute the cuts: ${error}`, es: `El motor no pudo calcular los cortes: ${error}` }} />
          ) : points ? (
            <div ref={host} className="dh-fill" data-state="ready" style={{ minHeight: '10rem', position: 'relative', overflow: 'hidden' }} />
          ) : (
            <Pending label={{ en: 'The engine is computing the focal volume', es: 'El motor está calculando el volumen focal' }} />
          )}
          {slabs && points && (
            <table className="sr-only">
              <caption>{t('Voxels drawn in each plane', 'Vóxeles dibujados en cada plano')}</caption>
              <thead>
                <tr>
                  <th>{t('plane', 'plano')}</th>
                  <th>{t('position (um)', 'posición (um)')}</th>
                  <th>{t('through trap', 'por la trampa')}</th>
                  <th>{t('voxels', 'vóxeles')}</th>
                </tr>
              </thead>
              <tbody>
                {slabs.map((s, i) => (
                  <tr key={`${s.plane}-${s.posUm}`}>
                    <td>{s.plane}</td>
                    <td>{fmt(s.posUm, { decimals: 2 })}</td>
                    <td>{s.trapId}</td>
                    <td>{fmt(points.perSlab[i], { decimals: 0 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Fill>
    </PlotCard>
  );
}
