// The acceptance measurements of the beyond-the-state-of-the-art rows that the benchmark matrix cannot reproduce, as the SDD records them.
// The benchmark scores every method on the same geometries, devices and budgets; three claims are measured by a test that does something
// the matrix does not: BS-1 over five seeds on the crosstalk device and on the full C08 device, BS-2 on the transient intensity of a moving
// trap between frames, BS-4 over an ensemble of residual aberrations and over pointing errors. Their numbers are written here once, with the
// SDD row each is read from, and `data.test.ts` fails when a number is no longer in that row of `docs/design/SDD.md`, so this file cannot
// drift from the design record. The page shows them in a column of their own, labelled as recorded, apart from what it reads from the
// benchmark document at run time.

export interface RecordedClaim {
  /** The ladder row in the SDD ("Method ladder" table). */
  row: 'BS-1' | 'BS-2' | 'BS-4';
  /** The test that measures it. */
  test: string;
  /** Every number the page shows from this record; each must appear in the SDD row. */
  numbers: Record<string, number>;
}

export const RECORDED: Record<string, RecordedClaim> = {
  'BS-1': {
    row: 'BS-1',
    test: 'tests/methods/beyond/test_b1_device_wgs.py',
    numbers: {
      /** Median of the factor by which B1 lowers the relative standard deviation below the corrected M07 on the crosstalk device. */
      medianFactor: 25.8,
      lowFactor: 15.9,
      highFactor: 33.3,
      seeds: 5,
      /** B1's efficiency over M07's, in the same runs. */
      efficiencyRatio: 0.995,
      /** The ratio of the means on the C08 device (4-bit phase, crosstalk, fill factor and flicker) over the three seeds of the bake's expected ranges. */
      fullDeviceFactor: 2.0,
    },
  },
  'BS-2': {
    row: 'BS-2',
    test: 'tests/methods/beyond/test_b2_flicker_bounded.py',
    numbers: {
      /** The acceptance task: the minimum transient intensity of a moving trap over its mean, B2 and LPI. */
      b2Low: 0.916,
      b2High: 0.926,
      lpiLow: 0.551,
      lpiHigh: 0.709,
      /** The peak step per frame, in Fourier units, of the frames the method names for a move (a bound set on C10's sort). */
      stepLimit: 0.2,
      /** The peak step per frame of the acceptance task itself, 13 frames for a move of 2 Fourier units. */
      acceptancePeakStep: 0.31,
      /** Long lattice moves: the medians of two lattices and the seeds that meet 0.9 of the mean. */
      longMedianA: 0.933,
      longMedianB: 0.936,
      longSeedsMet: 6,
      longSeeds: 8,
      /** C10's long sort on M16's own plan: B2 needs the end phases and this many frames; its range and median over the seeds that
       *  reach the threshold (one seed collapses on its phase path), and the LPI range. */
      c10Frames: 137,
      c10B2Median: 0.911,
      c10B2Low: 0.902,
      c10B2High: 0.917,
      c10LpiLow: 0.360,
      c10LpiHigh: 0.690,
      c10SeedsMet: 5,
      c10Seeds: 6,
      /** The equal-frame comparison on C10: the frames at which linear phase interpolation leads in every seed. */
      c10EqualFrames: 25,
      /** 1 when linear phase interpolation leads in every seed at those equal frames (0 would mean B2 does). */
      c10LpiLeadsAtEqualFrames: 1,
      /** The criterion of the claim. */
      threshold: 0.9,
    },
  },
  'BS-4': {
    row: 'BS-4',
    test: 'tests/methods/beyond/test_b4_robust.py',
    numbers: {
      /** Median over three seeds of the factor on the 95th percentile of the relative standard deviation over a 200-sample ensemble of aberrations. */
      medianFactor: 1.435,
      lowFactor: 1.42,
      highFactor: 1.57,
      seeds: 3,
      efficiencyRatio: 0.982,
      ensemble: 200,
      /** The factor against pointing errors: measured, reported, not claimed. */
      pointingFactor: 1.04,
    },
  },
};
