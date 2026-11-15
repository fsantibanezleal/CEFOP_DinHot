// The App opens on the method the story's exit names (ADR-0070 deep links): `?method=` is read on the first load of the case the URL names and
// is honoured only when the case lists that method; any other value leaves the case's reference method.
import { describe, expect, it } from 'vitest';
import { initialMethod, shortReason } from './Workbench';

const methods = ['M01', 'M06', 'M07', 'B1'];

describe('initialMethod', () => {
  it('opens the method named by ?method= when the case has it', () => {
    expect(initialMethod('?case=C08_device_limited&view=hologram&method=M07', 'C08_device_limited', methods, 'B1')).toBe('M07');
  });
  it('opens the reference method when the parameter names a method the case lacks', () => {
    expect(initialMethod('?case=C08_device_limited&method=M99', 'C08_device_limited', methods, 'B1')).toBe('B1');
    expect(initialMethod('?case=C08_device_limited&method=', 'C08_device_limited', methods, 'B1')).toBe('B1');
  });
  it('opens the reference method when there is no parameter', () => {
    expect(initialMethod('?case=C08_device_limited', 'C08_device_limited', methods, 'B1')).toBe('B1');
    expect(initialMethod('', 'C08_device_limited', methods, 'B1')).toBe('B1');
  });
  it('applies to the case the URL names only', () => {
    expect(initialMethod('?case=C02_grid_feedback&method=M07', 'C08_device_limited', methods, 'B1')).toBe('B1');
  });
  it('applies to the default case when the URL names none', () => {
    expect(initialMethod('?method=M06', 'C08_device_limited', methods, 'B1')).toBe('M06');
  });
});

describe('the rail says why WebGPU is not used, in the language of the reader', () => {
  it('translates the engine reasons it knows and shortens the others', () => {

    expect(shortReason('WebGPU has no adapter (requestAdapter returned null: headless shell, blocklisted GPU or no driver)', 'es')).toBe('el navegador no ofrece un adaptador WebGPU');
    expect(shortReason('WebGPU has no adapter (requestAdapter returned null)', 'en')).toBe('the browser offers no WebGPU adapter');
    expect(shortReason('the case device model (quantization, crosstalk) is evaluated on the CPU path only', 'es')).toBe('el modelo del dispositivo del caso corre sólo en CPU');
    expect(shortReason('something else: details')).toBe('something else');
  });
});
