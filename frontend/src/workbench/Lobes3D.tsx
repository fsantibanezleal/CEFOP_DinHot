// V6, 3D lobes: do traps in different planes overlap. The third independent variable is z, which a 2D map cannot carry for a
// multi-plane array (rubric section 4). Each trap is drawn as the iso-surface of its own focus: a Gaussian envelope with the
// diffraction-limited lateral width (FWHM 0.51 lambda / NA) and an axial width of two Rayleigh ranges (FWHM), scaled by the trap's
// relative intensity. This is a MODEL of the lobes from the setup and the per-trap intensities, not the computed 3D field, and the
// card says so. The overlap count is made at true size; the drawing may be magnified so a lobe a micrometre wide is visible in an
// array hundreds of micrometres across, and the magnification is stated.
// The scene renders on demand (never in a loop): orbit by dragging or with the arrow keys, zoom with the wheel (focused) or + and -.
import { PlotCard } from '@fasl-work/caos-app-shell';
import { useEffect, useMemo, useRef, useState } from 'react';
import { rayleighUm } from '../lib/ort';
import { cardOf } from './HologramGroup';
import { useSelection, type Selection } from './model';
import { Fill, Unavailable, useActions, useFmt, useStateKey, useT } from './ui';

interface Lobe {
  id: number;
  x: number;
  y: number;
  z: number;
  /** Semi-axes at the chosen threshold (true size, micrometres); 0 when the trap is dimmer than the threshold. */
  axy: number;
  az: number;
  rel: number;
}

const LN = (x: number) => Math.log(x);

export function lobesOf(sel: Selection, threshold: number): Lobe[] {
  const s = sel.data.manifest.params.setup;
  const sxy = (0.51 * s.wavelength_nm * 1e-3) / s.na / 2.355;
  const sz = (2 * rayleighUm(s)) / 2.355;
  const rel = sel.result?.trapI ?? [];
  return sel.traps.map((t, i) => {
    const r = rel[i] ?? 1;
    const level = threshold / Math.max(r, 1e-9);
    const k = level < 1 ? Math.sqrt(2 * LN(1 / level)) : 0;
    return { id: t.id, x: t.x_um, y: t.y_um, z: t.z_um, axy: sxy * k, az: sz * k, rel: r };
  });
}

/** Pairs of lobes whose ellipsoids (sum of semi-axes) overlap at true size; null above 400 lobes (the pairs would be 80 000). */
export function overlaps(lobes: readonly Lobe[]): { pairs: number; checked: number } | null {
  if (lobes.length > 400) return null;
  let pairs = 0;
  let checked = 0;
  for (let i = 0; i < lobes.length; i++) {
    for (let j = i + 1; j < lobes.length; j++) {
      const a = lobes[i];
      const b = lobes[j];
      checked++;
      const sxy = a.axy + b.axy;
      const sz = a.az + b.az;
      if (sxy <= 0 || sz <= 0) continue;
      const d = ((a.x - b.x) / sxy) ** 2 + ((a.y - b.y) / sxy) ** 2 + ((a.z - b.z) / sz) ** 2;
      if (d < 1) pairs++;
    }
  }
  return { pairs, checked };
}

export function Lobes3D({ sel }: { sel: Selection }) {
  const live = useSelection() ?? sel;
  const { t } = useT();
  const fmt = useFmt();
  const stateKey = useStateKey();
  const act = useActions();
  const host = useRef<HTMLDivElement | null>(null);
  const [threshold, setThreshold] = useState(0.5);
  const [failed, setFailed] = useState<string | null>(null);
  const lobes = useMemo(() => lobesOf(live, threshold), [live, threshold]);
  const ov = useMemo(() => overlaps(lobes), [lobes]);
  const c = cardOf(live);
  const extent = useMemo(() => {
    const m = Math.max(...live.traps.map((tr) => Math.max(Math.abs(tr.x_um), Math.abs(tr.y_um), Math.abs(tr.z_um))), 1);
    return m;
  }, [live.traps]);
  const widest = Math.max(...lobes.map((l) => l.axy), 1e-9);
  const magnify = Math.max(1, Math.round((0.04 * extent) / widest));

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let disposed = false;
    let cleanup = () => undefined as void;
    void import('three').then((THREE) => {
      if (disposed) return;
      try {
        const css = getComputedStyle(document.documentElement);
        const col = (name: string) => new THREE.Color(css.getPropertyValue(name).trim() || '#888888');
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        const w = Math.max(el.clientWidth, 200);
        const h = Math.max(el.clientHeight, 160);
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        el.appendChild(renderer.domElement);
        renderer.domElement.setAttribute('data-drawn', 'true');
        renderer.domElement.style.display = 'block';
        const scene = new THREE.Scene();
        scene.add(new THREE.AmbientLight(0xffffff, 1.1));
        const light = new THREE.DirectionalLight(0xffffff, 1.4);
        light.position.set(1, 2, 3);
        scene.add(light);
        const meshes: { mesh: import('three').Mesh; id: number }[] = [];
        for (const l of lobes) {
          if (l.axy <= 0) continue;
          const m = new THREE.Mesh(
            new THREE.SphereGeometry(1, 20, 14),
            new THREE.MeshStandardMaterial({ color: l.id === live.trapId ? col('--color-accent') : col('--color-good'), transparent: true, opacity: 0.55 }),
          );
          m.position.set(l.x, l.z, l.y);
          m.scale.set(l.axy * magnify, l.az * magnify, l.axy * magnify);
          scene.add(m);
          meshes.push({ mesh: m, id: l.id });
        }
        const camera = new THREE.PerspectiveCamera(40, w / h, extent / 100, extent * 100);
        const state = { az: 0.8, el: 0.5, dist: extent * 3.2 };
        const draw = () => {
          camera.position.set(state.dist * Math.cos(state.el) * Math.sin(state.az), state.dist * Math.sin(state.el), state.dist * Math.cos(state.el) * Math.cos(state.az));
          camera.lookAt(0, 0, 0);
          renderer.render(scene, camera);
        };
        draw();
        let down: { x: number; y: number; moved: boolean } | null = null;
        const dom = renderer.domElement;
        dom.tabIndex = 0;
        dom.setAttribute('role', 'img');
        dom.setAttribute('aria-label', t('3D lobes of the traps; drag to orbit', 'Lóbulos 3D de las trampas; arrastre para orbitar'));
        const pd = (e: PointerEvent) => {
          down = { x: e.clientX, y: e.clientY, moved: false };
          dom.setPointerCapture(e.pointerId);
          dom.focus();
        };
        const pm = (e: PointerEvent) => {
          if (!down) return;
          const dx = e.clientX - down.x;
          const dy = e.clientY - down.y;
          if (Math.hypot(dx, dy) > 3) down.moved = true;
          state.az -= dx * 0.01;
          state.el = Math.max(-1.5, Math.min(1.5, state.el + dy * 0.01));
          down.x = e.clientX;
          down.y = e.clientY;
          draw();
        };
        const pu = (e: PointerEvent) => {
          if (down && !down.moved) {
            const box = dom.getBoundingClientRect();
            const ray = new THREE.Raycaster();
            ray.setFromCamera(new THREE.Vector2(((e.clientX - box.left) / box.width) * 2 - 1, -((e.clientY - box.top) / box.height) * 2 + 1), camera);
            const hit = ray.intersectObjects(meshes.map((m) => m.mesh))[0];
            act.selectTrap(hit ? (meshes.find((m) => m.mesh === hit.object)?.id ?? null) : null);
          }
          down = null;
        };
        const wheel = (e: WheelEvent) => {
          if (document.activeElement !== dom && !e.ctrlKey && !e.metaKey) return;
          e.preventDefault();
          state.dist = Math.max(extent * 0.3, Math.min(extent * 20, state.dist * (e.deltaY < 0 ? 0.88 : 1.14)));
          draw();
        };
        const key = (e: KeyboardEvent) => {
          const step = 0.08;
          if (e.key === 'ArrowLeft') state.az -= step;
          else if (e.key === 'ArrowRight') state.az += step;
          else if (e.key === 'ArrowUp') state.el = Math.min(1.5, state.el + step);
          else if (e.key === 'ArrowDown') state.el = Math.max(-1.5, state.el - step);
          else if (e.key === '+' || e.key === '=') state.dist *= 0.88;
          else if (e.key === '-') state.dist *= 1.14;
          else if (e.key === '0') Object.assign(state, { az: 0.8, el: 0.5, dist: extent * 3.2 });
          else return;
          e.preventDefault();
          draw();
        };
        dom.addEventListener('pointerdown', pd);
        dom.addEventListener('pointermove', pm);
        dom.addEventListener('pointerup', pu);
        dom.addEventListener('wheel', wheel, { passive: false });
        dom.addEventListener('keydown', key);
        cleanup = () => {
          dom.removeEventListener('pointerdown', pd);
          dom.removeEventListener('pointermove', pm);
          dom.removeEventListener('pointerup', pu);
          dom.removeEventListener('wheel', wheel);
          dom.removeEventListener('keydown', key);
          for (const m of meshes) {
            m.mesh.geometry.dispose();
            (m.mesh.material as import('three').Material).dispose();
          }
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
    // the scene is rebuilt when the lobes, their magnification or the selected trap change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lobes, magnify, live.trapId, extent]);

  return (
    <PlotCard
      fill
      title={{ en: 'Trap lobes in 3D', es: 'Lóbulos de las trampas en 3D' }}
      {...c}
      dataKey={stateKey}
      note={{
        en: `A model of each trap's focus (Gaussian envelope, lateral FWHM 0.51 lambda / NA, axial FWHM two Rayleigh ranges, scaled by the trap's intensity), not the computed field. Drawn ${fmt(magnify, { decimals: 0 })} times larger than true size; the overlap count is at true size.`,
        es: `Un modelo del foco de cada trampa (envolvente gaussiana, FWHM lateral 0,51 lambda / NA, FWHM axial de dos rangos de Rayleigh, escalada por la intensidad de la trampa), no el campo calculado. Dibujado ${fmt(magnify, { decimals: 0 })} veces más grande que el tamaño real; el conteo de solapes es a tamaño real.`,
      }}
    >
      <Fill>
        <div className="dh-stack">
        <div className="dh-scrub">
          <label htmlFor="dh-threshold">{t('Threshold (fraction of the peak)', 'Umbral (fracción del pico)')}</label>
          <input id="dh-threshold" type="range" min={0.05} max={0.95} step={0.05} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          <output>{fmt(threshold, { decimals: 2 })}</output>
          <span role="status">
            {ov
              ? t(`${ov.pairs} of ${ov.checked} trap pairs overlap at this threshold.`, `${ov.pairs} de ${ov.checked} pares de trampas se solapan con este umbral.`)
              : t('Too many traps to count overlaps.', 'Demasiadas trampas para contar solapes.')}
          </span>
        </div>
        {failed ? (
          <Unavailable reason={{ en: `The 3D view needs WebGL, which this browser did not give (${failed}).`, es: `La vista 3D necesita WebGL, que este navegador no dio (${failed}).` }} />
        ) : (
          <div ref={host} className="dh-fill" data-state="ready" style={{ minHeight: '10rem' }} />
        )}
        <table className="sr-only">
          <caption>{t('Trap lobes at the threshold', 'Lóbulos de las trampas con el umbral')}</caption>
          <thead>
            <tr>
              <th>id</th>
              <th>x</th>
              <th>y</th>
              <th>z</th>
              <th>I/mean</th>
              <th>{t('lateral semi-axis (um)', 'semieje lateral (um)')}</th>
              <th>{t('axial semi-axis (um)', 'semieje axial (um)')}</th>
            </tr>
          </thead>
          <tbody>
            {lobes.slice(0, 200).map((l) => (
              <tr key={l.id}>
                <td>{l.id}</td>
                <td>{fmt(l.x, { decimals: 2 })}</td>
                <td>{fmt(l.y, { decimals: 2 })}</td>
                <td>{fmt(l.z, { decimals: 2 })}</td>
                <td>{fmt(l.rel, { decimals: 3 })}</td>
                <td>{fmt(l.axy, { decimals: 3 })}</td>
                <td>{fmt(l.az, { decimals: 3 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </Fill>
    </PlotCard>
  );
}
