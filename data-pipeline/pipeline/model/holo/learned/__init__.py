"""Training and evaluation code of the two learned model slots (cgh-net, warmstart-model). Offline only (ADR-0069, ADR-0074):
``convert`` and ``generators`` need numpy; ``torch_forward``, ``nets`` and ``export`` need the GPU lane (requirements-gpu.txt).
The method modules ``methods/learned/m17_cgh_net.py`` and ``b3_warm_start.py`` need only numpy and onnxruntime."""
