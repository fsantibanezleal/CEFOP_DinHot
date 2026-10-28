"""The networks and their ONNX export (needs torch, onnx and onnxruntime: runs in .venv-gpu, skipped in .venv-pipeline)."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")

from pipeline.model.holo.learned import export, generators, nets  # noqa: E402
from pipeline.model.holo.learned import torch_forward as tf  # noqa: E402


@pytest.fixture(scope="module")
def warm_net():
    torch.manual_seed(0)
    n = nets.SetNet()
    n.chirp.weight.data.normal_(0, 0.01)
    return n.eval()


@pytest.fixture(scope="module")
def cgh_net():
    torch.manual_seed(0)
    return nets.CghNet(14).eval()


def test_set_net_is_permutation_equivariant_and_ignores_padding(warm_net):
    rng = np.random.default_rng(2)
    s = generators.sample_traps(rng, family="random")[:60]
    t, m = generators.pad_batch([s], 100)
    perm = rng.permutation(len(s))
    t2, m2 = generators.pad_batch([s[perm]], 100)
    t3, m3 = generators.pad_batch([s], len(s))
    with torch.no_grad():
        a = warm_net(torch.as_tensor(t), torch.as_tensor(m))[0, : len(s)]
        b = warm_net(torch.as_tensor(t2), torch.as_tensor(m2))[0, : len(s)]
        c = warm_net(torch.as_tensor(t3), torch.as_tensor(m3))[0]
    d = export.wrapped_diff(a.numpy()[perm], b.numpy())
    assert d.max() < 2e-3                 # float32 reduction order of the pooled context times the chirp coefficient
    assert export.wrapped_diff(a.numpy(), c.numpy()).max() < 2e-3
    assert torch.all(warm_net(torch.as_tensor(t), torch.as_tensor(m))[0, len(s):] == 0)


def test_cgh_net_inverse_transform_is_the_inverse_of_the_focal_fft(cgh_net):
    # the constant DFT and the checkerboard carry a centred focal field to the SLM exactly: fftshift(fft2(.)) returns it
    f = torch.randn(1, 2, 128, 128)
    fr, fi = f[:, 0:1], f[:, 1:2]
    cm, sm, ck = cgh_net.cm, cgh_net.sm, cgh_net.checker
    ar, ai = torch.matmul(cm, fr) - torch.matmul(sm, fi), torch.matmul(cm, fi) + torch.matmul(sm, fr)
    sr, si = torch.matmul(ar, cm) - torch.matmul(ai, sm), torch.matmul(ai, cm) + torch.matmul(ar, sm)
    slm = torch.complex(sr * ck, si * ck)
    back = torch.fft.fftshift(torch.fft.fft2(slm), dim=(-2, -1)) / (128 * 128)
    np.testing.assert_allclose(back.numpy(), torch.complex(fr, fi).numpy(), atol=2e-3)


def test_graphs_are_web_safe_small_and_have_the_contract_io(warm_net, cgh_net, tmp_path):
    export.export_cgh(cgh_net, tmp_path / "c.onnx")
    export.export_warm(warm_net, tmp_path / "w.onnx")
    for p in ("c.onnx", "w.onnx"):
        assert export.check_ops(tmp_path / p) == set(), export.check_ops(tmp_path / p)
    assert (tmp_path / "c.onnx").stat().st_size <= 5 * 1024 * 1024
    assert (tmp_path / "w.onnx").stat().st_size <= 1024 * 1024
    i, o = export.io_spec(tmp_path / "c.onnx")
    assert i == [{"name": "target", "shape": [1, 1, 128, 128], "dtype": "float32"}]
    assert o == [{"name": "phase", "shape": [1, 1, 128, 128], "dtype": "float32"}]
    i, o = export.io_spec(tmp_path / "w.onnx")
    assert i == [{"name": "traps", "shape": [1, 1024, 4], "dtype": "float32"}, {"name": "mask", "shape": [1, 1024], "dtype": "float32"}]
    assert o == [{"name": "trap_phase", "shape": [1, 1024], "dtype": "float32"}]


def test_warmstart_graph_equals_torch_within_1e5(warm_net, tmp_path):
    export.export_warm(warm_net, tmp_path / "w.onnx")
    rng = np.random.default_rng(4)
    ins = [generators.pad_batch([generators.sample_traps(rng)], 1024) for _ in range(6)]
    assert export.parity(warm_net, tmp_path / "w.onnx", ins) < 1e-5


def test_cgh_graph_equals_torch_in_the_loss(cgh_net, tmp_path):
    """The phase of a near-zero SLM field is ill-conditioned (atan2), so the graph is compared where it matters: the accuracy of
    the mask. The trained model's per-pixel parity is measured and stored by ``train.release``."""
    export.export_cgh(cgh_net, tmp_path / "c.onnx")
    sess = export.session(tmp_path / "c.onnx")
    amp = tf.input_amplitude(128)
    for i in range(3):
        a = generators.sample_target(np.random.default_rng(i))[None, None]
        with torch.no_grad():
            p_t = cgh_net(torch.as_tensor(a))
        p_o = torch.as_tensor(sess.run(None, {"target": a})[0])
        ac_t = tf.accuracy(torch.as_tensor(a)[:, 0], tf.focal_intensity(p_t[:, 0], amp))
        ac_o = tf.accuracy(torch.as_tensor(a)[:, 0], tf.focal_intensity(p_o[:, 0], amp))
        assert abs(float(ac_t) - float(ac_o)) < 1e-4


def test_adversarial_an_op_outside_the_list_is_seen(tmp_path):
    import onnx
    from onnx import TensorProto, helper
    node = helper.make_node("LayerNormalization", ["x", "s"], ["y"], axis=-1)
    g = helper.make_graph([node], "g", [helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 4]),
                                       helper.make_tensor_value_info("s", TensorProto.FLOAT, [4])],
                          [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 4])])
    p = tmp_path / "bad.onnx"
    onnx.save(helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)]), str(p))
    assert export.check_ops(p) == {"LayerNormalization"}
