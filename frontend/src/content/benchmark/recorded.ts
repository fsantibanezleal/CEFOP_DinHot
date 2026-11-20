import { ID } from '../../lib/methodIds';
// The acceptance measurements of the beyond-the-state-of-the-art rows that the benchmark matrix cannot reproduce, as the SDD records them.
// The benchmark scores every method on the same geometries, devices and budgets; three claims are measured by a test that does something
// the matrix does not: B1 over five seeds on the crosstalk and the 4-bit devices and on the full C08 device, B2 on the transient intensity of a moving
// trap between frames, B4 over an ensemble of residual aberrations and over pointing errors. Their numbers are written here once, with the
// SDD row each is read from, and `data.test.ts` fails when a number is no longer in that row of `docs/design/SDD.md`, so this file cannot
// drift from the design record. The page shows them in a column of their own, labelled as recorded, apart from what it reads from the
// benchmark document at run time.

export interface RecordedClaim {
  /** The ladder row in the SDD ("Method ladder" table). */
  row: string;
  /** The test that measures it. */
  test: string;
  /** Every number the page shows from this record; each must appear in the SDD row. */
  numbers: Record<string, number>;
}

export const RECORDED: Record<string, RecordedClaim> = {
  [ID.B1]: {
    row: ID.B1,
    test: 'tests/methods/beyond/test_b1_device_wgs.py',
    numbers: {
      /** Geometric mean of the factor by which B1 (default: no weight update) lowers the relative standard deviation below phase-fixed WGS on
       *  the crosstalk device, with its 95 percent interval, over five seeds (device-aware paper, `beyond_numbers.tex` ablBFullFac, ablBFullFacLo, ablBFullFacHi). */
      geoMeanFactor: 201.3,
      lowFactor: 132.9,
      highFactor: 304.9,
      seeds: 5,
      /** B1's efficiency over M07's, in the same runs (ablBFullEff). */
      efficiencyRatio: 0.999,
      /** The same factor on the 4-bit device with crosstalk, fill factor and flicker (ablBFFullFac and its interval), five seeds, and its efficiency ratio. */
      fourBitFactor: 23.5,
      fourBitLow: 18.6,
      fourBitHigh: 29.6,
      fourBitEfficiency: 0.997,
      /** The normalized-error loss of Schroff et al. 2023 through the same warm start, device model and conjugate gradient (`tab_schroff.tex`):
       *  the crosstalk device and the 4-bit device. The refinement's own elements add nothing measurable over it. */
      schroffFactor: 159.9,
      schroffLow: 107.0,
      schroffHigh: 239.1,
      schroffFourBitFactor: 26.1,
      schroffFourBitLow: 20.2,
      schroffFourBitHigh: 33.9,
      /** The ratio of the means on the C08 device (4-bit phase, crosstalk, fill factor and flicker) over the three seeds of the bake's expected ranges (bakeCeightRatioThree). */
      fullDeviceFactor: 2.0,
      /** The benchmark's geometries on the C08 device at 100 iterations that meet both thresholds, of those with both methods (benchOneDevPass, benchOneDevN). */
      benchPass: 4,
      benchGeometries: 6,
    },
  },
  [ID.B2]: {
    row: ID.B2,
    test: 'tests/methods/beyond/test_b2_flicker_bounded.py',
    numbers: {
      /** The acceptance task, six seeds of the flicker-bounded sequences paper (`flicker_numbers.tex`, 13 frames): the minimum transient intensity of a
       *  moving trap over its mean, B2 and LPI, and the per-frame GS with phase induction of Kim et al. 2019 at five and at ten iterations per frame.
       *  The acceptance test itself asserts at least 0.9 on its seeds 1 to 3. */
      accSeeds: 6,
      b2Low: 0.915,
      b2High: 0.932,
      lpiLow: 0.551,
      lpiHigh: 0.709,
      kimFiveLow: 0.918,
      kimFiveHigh: 0.965,
      kimTenLow: 0.88,
      kimTenHigh: 0.966,
      /** The peak step per frame, in Fourier units, of the frames the method names for a move (a bound set on C10's sort). */
      stepLimit: 0.2,
      /** The peak step per frame of the acceptance task itself, 13 frames for a move of 2 Fourier units. */
      acceptancePeakStep: 0.31,
      /** The largest phase step between frames of the acceptance task, B2 and the per-frame method at five iterations, in radians (accBStepMax, accKimFiveStepMax). */
      b2PhaseStep: 0.077,
      kimPhaseStep: 0.408,
      /** Long lattice moves: the medians of two lattices and the seeds that meet 0.9 of the mean. */
      longMedianA: 0.933,
      longMedianB: 0.936,
      longSeedsMet: 6,
      longSeeds: 8,
      /** C10's long sort on M16's own plan, six seeds, at the frames of the bound: B2 range and median, the LPI range, the per-frame method at five
       *  iterations (range), and the seeds that meet the threshold. */
      c10Frames: 137,
      c10B2Median: 0.914,
      c10B2Low: 0.909,
      c10B2High: 0.917,
      c10LpiLow: 0.044,
      c10LpiHigh: 0.738,
      c10KimFiveLow: 0.922,
      c10KimFiveHigh: 0.956,
      c10SeedsMet: 6,
      c10Seeds: 6,
      /** The equal-frame comparison on C10: at this many frames no method reaches 0.9, B2 is at most c10EqualB2Max, and linear phase interpolation is
       *  above B2 on c10LpiLeadsEqual of the six seeds. */
      c10EqualFrames: 25,
      c10EqualB2Max: 0.412,
      c10LpiLeadsEqual: 4,
      /** The criterion of the claim. */
      threshold: 0.9,
    },
  },
  [ID.B4]: {
    row: ID.B4,
    test: 'tests/methods/beyond/test_b4_robust.py',
    numbers: {
      /** Median over three seeds of the factor on the 95th percentile of the relative standard deviation over a 200-sample ensemble of aberrations. */
      medianFactor: 1.435,
      lowFactor: 1.42,
      highFactor: 1.57,
      seeds: 3,
      efficiencyRatio: 0.982,
      ensemble: 200,
      /** The same over ten seeds (the paper's headline): median with its bootstrap interval, the paper's statistic (robust_numbers.tex
       *  ratioAllMed, ratioAllCiLo, ratioAllCiHi), and the seeds whose own bootstrap interval clears the criterion. */
      tenSeedMedian: 1.439,
      tenSeedCiLo: 1.38,
      tenSeedCiHi: 1.48,
      tenSeeds: 10,
      tenSeedsClear: 8,
      /** The factor against pointing errors: measured, reported, not claimed. */
      pointingFactor: 1.04,
      /** A displacement prior alone, 100 steps (five times the budget), at 0.10 focal bins: the factor and the efficiency ratio (manuscript of the method). */
      pointingLongFactor: 1.48,
      pointingLongEfficiency: 0.912,
      pointingLongBins: 0.1,
    },
  },
};
