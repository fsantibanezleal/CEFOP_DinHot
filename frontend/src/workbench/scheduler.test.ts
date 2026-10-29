// D1: a change of a control starts a run, a second change cancels the first. The scheduler is held with fake timers and a fake client,
// then the same rule is held end to end over the real engine client with a loopback in place of the Web Worker, so the message that
// stops the worker and the rejection of the first run are the client's own.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AbortError, createEngineClient, type WorkerLike } from '../engine/holo/client';
import type { InMsg, OutMsg } from '../engine/holo/runner';
import { LiveScheduler } from './scheduler';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

/** A job that records its start and ends when `finish` is called. */
function pendingJob(log: string[], name: string) {
  let finish: () => void = () => undefined;
  let current: () => boolean = () => false;
  const done = new Promise<void>((r) => (finish = r));
  const job = async (isCurrent: () => boolean) => {
    current = isCurrent;
    log.push(`start ${name}`);
    await done;
    if (isCurrent()) log.push(`answer ${name}`);
  };
  return { job, finish: () => finish(), isCurrent: () => current() };
}

describe('the live scheduler', () => {
  it('starts a run only after the pause with no further change, never on its own', async () => {
    const log: string[] = [];
    const cancel = vi.fn();
    const s = new LiveScheduler({ cancel });
    const a = pendingJob(log, 'A');
    s.submit(a.job);
    await vi.advanceTimersByTimeAsync(150);
    expect(log).toEqual([]);
    const b = pendingJob(log, 'B');
    s.submit(b.job); // a second change inside the pause replaces the first before it starts
    await vi.advanceTimersByTimeAsync(150);
    expect(log).toEqual([]);
    await vi.advanceTimersByTimeAsync(60);
    expect(log).toEqual(['start B']);
    expect(cancel).not.toHaveBeenCalled(); // nothing was running when A was replaced
    b.finish();
    await vi.advanceTimersByTimeAsync(0);
    expect(log).toEqual(['start B', 'answer B']);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(log).toHaveLength(2); // nothing restarts at rest (G8)
  });

  it('a second change cancels the run in flight and its late answer is dropped', async () => {
    const log: string[] = [];
    const cancel = vi.fn();
    const s = new LiveScheduler({ cancel });
    const a = pendingJob(log, 'A');
    s.submit(a.job);
    await vi.advanceTimersByTimeAsync(200);
    expect(log).toEqual(['start A']);
    expect(s.busy).toBe(true);
    const b = pendingJob(log, 'B');
    s.submit(b.job);
    expect(cancel).toHaveBeenCalledTimes(1); // the engine is told at once
    expect(a.isCurrent()).toBe(false);
    await vi.advanceTimersByTimeAsync(200);
    expect(log).toEqual(['start A', 'start B']);
    a.finish(); // A's answer arrives late
    b.finish();
    await vi.advanceTimersByTimeAsync(0);
    expect(log).toEqual(['start A', 'start B', 'answer B']);
  });

  it('cancel() stops the run and nothing starts until the next submit', async () => {
    const log: string[] = [];
    const cancel = vi.fn();
    const s = new LiveScheduler({ cancel });
    const a = pendingJob(log, 'A');
    s.submit(a.job);
    await vi.advanceTimersByTimeAsync(200);
    s.cancel();
    expect(cancel).toHaveBeenCalledTimes(1);
    a.finish();
    await vi.advanceTimersByTimeAsync(5_000);
    expect(log).toEqual(['start A']);
  });

  it('a job that throws does not wedge the scheduler', async () => {
    const s = new LiveScheduler({ cancel: () => undefined });
    s.submit(async () => {
      throw new Error('boom');
    });
    await vi.advanceTimersByTimeAsync(200);
    expect(s.busy).toBe(false);
    const log: string[] = [];
    s.submit(async () => void log.push('next'));
    await vi.advanceTimersByTimeAsync(200);
    expect(log).toEqual(['next']);
  });
});

describe('over the engine client', () => {
  /** A worker that records what it is sent and answers only when told. */
  function loopback() {
    const sent: InMsg[] = [];
    const w: WorkerLike = {
      postMessage: (m) => void sent.push(m),
      terminate: () => undefined,
      onmessage: null,
      onerror: null,
    };
    const answer = (m: OutMsg) => w.onmessage?.({ data: m });
    return { w, sent, answer };
  }
  const params = { case_id: 'X' } as never;

  it('the second change cancels the first run: one cancel message, the first promise rejects with AbortError, the second is answered', async () => {
    const { w, sent, answer } = loopback();
    const client = createEngineClient(() => w);
    const sched = new LiveScheduler({ cancel: () => client.cancel() });
    const outcome: string[] = [];
    const submit = (name: string) =>
      sched.submit(async (isCurrent) => {
        try {
          await client.run({ params, method: 'M04', options: { iterations: name === 'A' ? 10 : 20 } });
          if (isCurrent()) outcome.push(`answered ${name}`);
        } catch (e) {
          outcome.push(`${name} ${e instanceof AbortError ? 'aborted' : 'failed'}`);
        }
      });
    submit('A');
    await vi.advanceTimersByTimeAsync(200);
    const runs = () => sent.filter((m) => m.op === 'run');
    expect(runs()).toHaveLength(1);
    submit('B');
    await vi.advanceTimersByTimeAsync(0);
    expect(sent.filter((m) => m.op === 'cancel')).toHaveLength(1);
    expect(outcome).toEqual(['A aborted']);
    await vi.advanceTimersByTimeAsync(200);
    expect(runs()).toHaveLength(2);
    const second = runs()[1] as Extract<InMsg, { op: 'run' }>;
    expect(second.options?.iterations).toBe(20);
    answer({ type: 'result', id: second.id, result: {} as never });
    await vi.advanceTimersByTimeAsync(0);
    expect(outcome).toEqual(['A aborted', 'answered B']);
  });
});
