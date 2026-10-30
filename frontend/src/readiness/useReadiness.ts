import { useEffect, useState } from 'react';
import type { Readiness } from '../lib/contract.types';
import { loadReadiness } from './readiness';

/** The readiness document: undefined while it loads, null when it could not be read, else the document. */
export function useReadiness(): Readiness | null | undefined {
  const [doc, setDoc] = useState<Readiness | null | undefined>(undefined);
  useEffect(() => {
    let live = true;
    void loadReadiness().then((d) => {
      if (live) setDoc(d);
    });
    return () => {
      live = false;
    };
  }, []);
  return doc;
}
