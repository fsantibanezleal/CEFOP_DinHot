// The engine ids of the ladder as data keys, never as text (CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0): code reaches a method
// through `ID.M07`, so no string literal in the app is an id a reader could be shown. The keys are the registry's, one per method of the SDD ladder.
const KEYS = { M01: 0, M02: 0, M03: 0, M04: 0, M05: 0, M06: 0, M07: 0, M08: 0, M09: 0, M10: 0, M11: 0, M12: 0, M13: 0, M14: 0, M15: 0, M16: 0, M17: 0, M18: 0, M19: 0, B1: 0, B2: 0, B3: 0, B4: 0, B5: 0 };

export type MethodKey = keyof typeof KEYS;
export const ID = Object.fromEntries(Object.keys(KEYS).map((k) => [k, k])) as { [K in MethodKey]: K };
