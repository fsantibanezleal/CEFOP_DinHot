"""The operator allow-list of the exported graphs (no torch needed, so the contract tests can read it)."""
from __future__ import annotations

OPSET = 17
# Operators this export may contain: each is in the WebGL operator table of onnxruntime-web and in the CPU provider that its
# WASM build compiles; nothing outside this list (no DFT, LayerNormalization, GroupNorm, Attention, Einsum, Resize) is used.
WEB_SAFE_OPS = frozenset({
    "Add", "Sub", "Mul", "Div", "Neg", "Sqrt", "Relu", "Sigmoid", "Tanh", "Conv", "ConvTranspose", "MatMul", "Gemm", "Softmax",
    "Concat", "Reshape", "Transpose", "Unsqueeze", "Squeeze", "Slice", "Shape", "Gather", "Constant", "ReduceMean", "ReduceSum",
    "Cast", "Identity", "Flatten", "Expand", "Pad", "Exp", "Log", "Max", "Min", "Clip", "Split", "Sin", "Cos", "Atan", "Where",
    "Less", "Greater", "Equal", "And", "Not", "Abs", "Sign", "ConstantOfShape",
})
