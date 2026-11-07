// A reader meets each method by its name, never by its engine id (CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0):
// the label of a chip, a chart, a legend or a caption is the name from the ladder, in both languages.
import { describe, expect, it } from 'vitest';
import { METHOD_NAMES, methodLabel, methodName } from './model';

const ID = /\b([MB]\d{1,2})\b/;

describe('the label of a method', () => {
  it('is its name in both languages, with no engine id in it', () => {
    for (const id of Object.keys(METHOD_NAMES)) {
      for (const lang of ['en', 'es'] as const) {
        expect(methodLabel(id)[lang], `${id} ${lang}`).toBe(methodName(id)[lang]);
        expect(methodLabel(id)[lang], `${id} ${lang}`).not.toMatch(ID);
      }
    }
  });
  it('names every method of the ladder, M01 to M19 and B1 to B5, and no two methods share a name', () => {
    const ids = Object.keys(METHOD_NAMES);
    expect(ids).toHaveLength(24);
    for (const lang of ['en', 'es'] as const) expect(new Set(ids.map((id) => methodName(id)[lang])).size).toBe(ids.length);
  });
});
