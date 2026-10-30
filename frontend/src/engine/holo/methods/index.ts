/**
 * Registry of the live methods.
 *
 * Python counterpart: `methods/__init__.py` (the registry of every method). Only the methods whose Python `SPEC.lane` is `live`
 * or `both` are ported here; every other id (baked-only methods M09, M13, M18, B1, B2, B4, B5, the learned B3) raises `NotLive`,
 * which the workbench shows as "replayed from the bake". There is never a silent fallback to another method.
 */
import { type MethodModule, type MethodSpec, NotLive } from '../types';
import { baselineMethods } from './baseline';
import { controlMethods } from './control';
import { optimMethods } from './optim';

const ALL: MethodModule[] = [...baselineMethods, ...controlMethods, ...optimMethods].sort((a, b) => (a.spec.id < b.spec.id ? -1 : 1));
const BY_ID = new Map(ALL.map((m) => [m.spec.id, m]));

/** Ids of the ported (live) methods, sorted. */
export const liveMethodIds = (): string[] => ALL.map((m) => m.spec.id);

export const liveSpecs = (): MethodSpec[] => ALL.map((m) => m.spec);

/** The ported method with that id; `NotLive` for any other id. */
export function getMethod(id: string): MethodModule {
  const m = BY_ID.get(id);
  if (!m) throw new NotLive(id);
  return m;
}
