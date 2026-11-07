// No engine id reaches a reader (CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0): the strings and the JSX text of the app name each
// method by its name. A string that is exactly an id is a data key (it reads an artifact or calls the engine) and is never drawn; any other string
// that holds an id among other words is text a reader sees. The scan reads every source file, comments excepted, the way
// scripts/check_internal_names.py does, and adds the proposed methods' ids B1 to B5, which that script reads as BS-1 to BS-5.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const ID = /(?<![\w-])(?:M\d{2}|B[1-5])(?![\w-])/;
const EXACT = /^(?:M\d{2}|B[1-5])$/;
const STRING = /'((?:\\.|[^'\\\n])*)'|"((?:\\.|[^"\\\n])*)"|`((?:\\.|[^`\\])*)`/g;
const JSX_TEXT = />([^<>{}]*[A-Za-z][^<>{}]*)</g;
const SRC = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.(test|gen)\.|\.d\.ts$/.test(name) ? [path] : [];
  });
}

/** The strings and JSX text of a source with an id among other words, as `file:line: text`. */
export function idsInText(path: string, text: string): string[] {
  const body = text
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '))
    .split('\n')
    .map((l) => l.replace(/(?<![:"'`\\])\/\/.*$/, ''))
    .join('\n');
  const hits: string[] = [];
  const line = (at: number) => body.slice(0, at).split('\n').length;
  for (const m of body.matchAll(STRING)) {
    const s = m[1] ?? m[2] ?? m[3] ?? '';
    if (ID.test(s) && !EXACT.test(s)) hits.push(`${path}:${line(m.index)}: ${s.slice(0, 80)}`);
  }
  for (const m of body.matchAll(JSX_TEXT)) {
    if (ID.test(m[1]) && !/mv\(/.test(m[1])) hits.push(`${path}:${line(m.index)}: ${m[1].trim().slice(0, 80)}`);
  }
  return hits;
}

describe('the reader surfaces carry no engine id', () => {
  it('flags an id among words and lets a data key through', () => {
    expect(idsInText('a.tsx', "const x = 'M07 random start';")).toHaveLength(1);
    expect(idsInText('a.tsx', 'const x = <p>the B1 hologram</p>;')).toHaveLength(1);
    expect(idsInText('a.tsx', "const x = `${n} cells of B3`;")).toHaveLength(1);
    expect(idsInText('a.tsx', "const x = trace.methods['M07'];")).toHaveLength(0);
    expect(idsInText('a.tsx', "// M07 is the key\nconst y = 1;")).toHaveLength(0);
  });

  it('every string and JSX text of the app names its methods', () => {
    const hits = sources(SRC).flatMap((p) => idsInText(p.slice(SRC.length), readFileSync(p, 'utf8')));
    expect(hits).toEqual([]);
  });
});
