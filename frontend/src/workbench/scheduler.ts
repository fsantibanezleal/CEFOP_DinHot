// The rule of the live lane, apart from React so a test can hold it: a change of a control submits a job; a job starts after a short
// pause with no further change (never on a timer of its own, G8); a later job cancels the one in flight (the engine stops within one
// iteration) and makes its late answer stale, so an old result can never replace a newer one or carry the wrong label.

export interface SchedulerOptions {
  /** Called when a running job is replaced or cancelled: the engine client's `cancel`. */
  cancel: () => void;
  /** The pause after the last change before the engine starts, in milliseconds. */
  delayMs?: number;
}

/** A job receives `isCurrent`: false once a later job or a cancel has replaced it, so it must drop its answer. */
export type Job = (isCurrent: () => boolean) => Promise<void>;

export class LiveScheduler {
  private seq = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private running = 0;
  private readonly delayMs: number;

  constructor(private readonly opts: SchedulerOptions) {
    this.delayMs = opts.delayMs ?? 200;
  }

  /** True while a job is between its start and its end. */
  get busy(): boolean {
    return this.running > 0;
  }

  /** Replace whatever is pending or running with `job`. */
  submit(job: Job): void {
    const id = ++this.seq;
    this.stop();
    this.timer = setTimeout(() => {
      this.timer = null;
      this.running++;
      const isCurrent = () => id === this.seq;
      void job(isCurrent)
        .catch(() => undefined)
        .finally(() => {
          this.running--;
        });
    }, this.delayMs);
  }

  /** Cancel the pending or running job; nothing starts until the next `submit`. */
  cancel(): void {
    this.seq++;
    this.stop();
  }

  /** The owner is gone: same as cancel. */
  dispose(): void {
    this.cancel();
  }

  private stop(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.running > 0) this.opts.cancel();
  }
}
