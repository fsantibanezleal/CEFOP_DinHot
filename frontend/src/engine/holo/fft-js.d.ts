// Types of fft.js 4.0.4 (the package ships loose `any` declarations): Float64 interleaved complex arrays, radix-4,
// power-of-two sizes only; `inverseTransform` divides by `size`.
declare module 'fft.js' {
  export default class FFT {
    constructor(size: number);
    readonly size: number;
    createComplexArray(): number[];
    transform(out: Float64Array, data: Float64Array): void;
    inverseTransform(out: Float64Array, data: Float64Array): void;
  }
}
