// The two colormaps of the workbench, as 256-entry lookup tables of 8-bit RGB (768 bytes each, base64). They are data, not
// styling: the only colour values outside the theme tokens (the shell's palette), because a heatmap needs a perceptually
// uniform map and the shell's tokens are categorical.
//  - PHASE_LUT: CET-C1 (cyclic_mrybm_35_75_c68), Peter Kovesi, colorcet 3.2.1, licence CC BY 4.0
//    (https://creativecommons.org/licenses/by/4.0/), https://colorcet.com ; Kovesi, "Good Colour Maps: How to Design Them",
//    arXiv:1509.03700. A cyclic map: the phase 0 and 2 pi are the same colour, so the wrap is not an edge.
//  - INTENSITY_LUT: inferno, Nathaniel Smith and Stefan van der Walt (matplotlib 3.11.2 _cm_listed.py), licence CC0.
// The attribution line is in ATTRIBUTION.md (Colormaps).
const PHASE_B64 = [
  '+YX4+oT2+4Pz/ILx/IHu/X/r/X7o/Xzl/Xri/Xje/Xbb/HTX/HLU+3DQ+23M+mvI+mnF+WfB+GS992K591+19l2y9Vuu9Fiq81am',
  '8lSj8VGf8E+b70yX7kqU7UiQ7EaM6kOI6UGE6D+B5j195Tt54zl14Tdx4DVt3jNq3DFm2i9i2S1e1yxa1SpW0yhT0SZPzyRLzSNH',
  'yyFEyR9Axx48xhw5xBs1whkywBguvhcrvRcnuxckuhchuRceuBgbtxkZthsWtR0UtR8RtSEPtSMNtSYMtSkKtisIti4HtzEGuDMG',
  'uDYFuTkFujsFuz4EvEEEvUMEvkYEv0gEwEsEwU0EwlAEw1IExFQExVcExlkFx1wFyF4FyWAFymMFymUFy2cFzGoFzWwFzm8FznEF',
  'z3MF0HYF0HgF0XoF0X0F0n8E0oEE04QE04YE1IkE1IsE1Y0E1Y8E1pIE1pQF1pYF1pgG15sH150I158K16AN1qIP1qQS1aUV1acY',
  '1Kgc0qkf0aoj0KonzqorzKsvyqszx6o3xao7wqk/v6lDvKhGuadKtqZOs6VSr6RVrKNZqaFcpaBgoZ9jnZ5mmp1plpttkppwjplz',
  'iZh2hZZ5gZV8fJR/d5OCc5GFbpCIaY+LY42OXoyRWYuUU4mXToiaSIadQ4SgPoOjOYGmNH+pL32sK3uvKHmyJXa1I3S4InG7Im++',
  'ImzBImnFJGbIJWPLJmDOKF3RKVrUK1fXLVTaLlHdME7gMUvjM0nlNUboN0TqOULsPEDuPj/wQT7yRD3zRz30ST31TD32Tz73Uj/3',
  'VUD4WEH4W0P5XkX5YUf5Y0n5Zkv5aU35a0/5blH5cFP5c1X5dVf5d1n5elv6fF36f176gmD6hGL6h2T6imX6jWf6kGn6k2r6lmv7',
  'mW37nG77oG/7o3H7p3L8qnP8rnT8sXX8tXb9uXf9vHj9wHn+w3r+x3v+ynz/zn3/0X7/1X//2ID/24H/34L/4oP/5YT/6IT/6oX/',
  '7YX/8Ib+8ob99Ib89ob794X5',
].join('');
const INFERNO_B64 = [
  'AAAEAQAFAQEGAQEIAgEKAgIMAgIOAwIQBAMSBAMUBQQXBgQZBwUbCAUdCQYfCgciCwckDAgmDQgpDgkrEAktEQowEgoyFAs0FQs3',
  'Fgs5GAw8GQw+GwxBHAxDHgxFHwxIIQxKIwxMJAxPJgxRKAtTKQtVKwtXLQtZLwpbMQpcMgpeNApfNglhOAliOQljOwlkPQllPglm',
  'QApnQgpoRApoRQppRwtqSQtqSgxrTAxrTQ1sTw1sUQ5sUg5tVA9tVQ9tVxBuWRBuWhFuXBJuXRJuXxNuYRNuYhRuZBVuZRVuZxZu',
  'aRZuahdubBhubRhubxlucRluchpudBpudRtudxxteBxteh1tfB1tfR5tfx5sgB9sgiBshCBrhSFrhyFriCJqiiJqjCNpjSNpjyRp',
  'kCVokiVokyZnlSZnlydmmCdmmihlmylknSlknypjoCpjoitioyxhpSxgpi1gqC5fqS5eqy9erTBdrjBcsDFbsTJaszJatDNZtjRY',
  'tzVXuTVWujZVvDdUvThTvzlSwDpRwTpQwztPxDxOxj1Nxz5MyD9LykBKy0FJzEJIzkNHz0RG0EVF0kZE00dD1EhC1UpB10s/2Ew+',
  '2U092k4821A73VE63lI431M34FU24VY14lc041kz5Fox5Vww5l0v514u6GAt6WEr6mMq62Qp62Yo7Gcm7Wkl7mok72wj724h8G8g',
  '8XEf8XMd8nQc83Yb83gZ9HkY9XsX9X0V9n4U9oAT94IS94QQ+IUP+IcO+IkM+YsL+YwK+Y4J+pAI+pIH+pQH+5YG+5cG+5kG+5sG',
  '+50H/J8H/KEI/KMJ/KUK/KYM/KgN/KoP/KwR/K4S/LAU/LIW/LQY+7Ya+7gd+7of+7wh+74j+sAm+sIo+sQq+sYt+ccv+cky+cs1',
  '+M03+M8699E999NA9tVD9tdG9dlJ9dtM9N1P9N9T9OFW8+Na8+Vd8uZh8uhl8upp8ext8e1x8e918fF58vJ98vSC8/WG8/aK9PiO',
  '9fmS9vqW+Pua+fyd+v2h/P+k',
].join('');

function decode(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export const PHASE_LUT = decode(PHASE_B64);
export const INTENSITY_LUT = decode(INFERNO_B64);

/** The RGB of a unit value (0 to 1) in a 256-entry table: nearest entry, clamped. */
export function lutRgb(lut: Uint8Array, u: number): [number, number, number] {
  const k = Math.max(0, Math.min(255, Math.round(u * 255))) * 3;
  return [lut[k], lut[k + 1], lut[k + 2]];
}
