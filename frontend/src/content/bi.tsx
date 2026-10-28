// Bilingual prose for the documentation pages: every paragraph is written in both languages where it is written.
import { useShellLang } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';

/** A translator for the current language: `t('English', 'Español')`. */
export function useT(): (en: string, es: string) => string {
  const lang = useShellLang();
  return (en, es) => (lang === 'es' ? es : en);
}

/** One paragraph in the current language. */
export function P({ en, es }: { en: ReactNode; es: ReactNode }) {
  const lang = useShellLang();
  return <p>{lang === 'es' ? es : en}</p>;
}

/** A bulleted list, item by item in the current language. */
export function L({ items }: { items: { en: ReactNode; es: ReactNode }[] }) {
  const lang = useShellLang();
  return (
    <ul>
      {items.map((it, i) => (
        <li key={i}>{lang === 'es' ? it.es : it.en}</li>
      ))}
    </ul>
  );
}
