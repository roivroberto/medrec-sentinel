import importlib

import pytest

from medrec_sentinel.llm.medgemma import extract_json_block, generate, load_model


def test_extract_json_block() -> None:
    txt = "prefix\n```json\n{\"a\": 1}\n```\nsuffix"
    assert extract_json_block(txt) == '{"a": 1}'


def test_extract_json_block_skips_invalid_fenced_json() -> None:
    txt = (
        "prefix\n"
        "```json\n{not json}\n```\n"
        "mid\n"
        "```json\n{\"a\": 2}\n```\n"
        "suffix"
    )
    assert extract_json_block(txt) == '{"a": 2}'


def test_extract_json_block_fallback_scans_for_array() -> None:
    txt = "prefix blah\n[1, 2, 3]\nsuffix"
    assert extract_json_block(txt) == "[1, 2, 3]"


def test_generate_passes_inputs_dict_and_uses_inference_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    import contextlib
    import types

    import medrec_sentinel.llm.medgemma as medgemma

    entered = {"inference": False}

    @contextlib.contextmanager
    def inference_mode():
        entered["inference"] = True
        yield

    fake_torch = types.SimpleNamespace(inference_mode=inference_mode)

    class FakeTensor:
        def __init__(self, shape: tuple[int, ...]):
            self.shape = shape
            self.moved_to = None

        def to(self, device: str):
            self.moved_to = device
            return self

    class FakeProcessor:
        def decode(self, _ids, skip_special_tokens: bool = True) -> str:
            return "```json\n{\"ok\": true}\n```"

    class FakeModel:
        device = "cpu"

        def generate(self, *, input_ids=None, attention_mask=None, **_kwargs):
            assert input_ids is not None
            assert attention_mask is not None
            return [[0, 1, 2, 3, 4]]

    monkeypatch.setattr(medgemma, "_MODEL", FakeModel())
    monkeypatch.setattr(medgemma, "_PROCESSOR", FakeProcessor())

    monkeypatch.setattr(medgemma, "_lazy_import_torch", lambda: fake_torch)

    def fake_render_prompt(_processor, _prompt: str):
        return {"input_ids": FakeTensor((1, 3)), "attention_mask": FakeTensor((1, 3))}

    monkeypatch.setattr(medgemma, "_render_prompt", fake_render_prompt)

    assert generate("hi", max_new_tokens=4, temperature=0.0) == '{"ok": true}'
    assert entered["inference"] is True


def test_load_model_raises_when_transformers_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None):
        if name == "transformers":
            raise ImportError("no transformers")
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="transformers"):
        load_model("google/medgemma-4b-it")


def test_generate_raises_when_transformers_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None):
        if name == "transformers":
            raise ImportError("no transformers")
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="transformers"):
        generate("hi", max_new_tokens=4, temperature=0.0)


def test_load_model_uses_4bit_nf4_and_moves_to_cuda_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import types

    import medrec_sentinel.llm.medgemma as medgemma

    medgemma._MODEL = None
    medgemma._PROCESSOR = None
    medgemma._MODEL_ID = None

    captured: dict[str, object] = {}

    class FakeBitsAndBytesConfig:
        def __init__(
            self,
            *,
            load_in_4bit: bool = False,
            llm_int8_enable_fp32_cpu_offload: bool = False,
            bnb_4bit_compute_dtype=None,
            bnb_4bit_quant_type: str = "fp4",
            bnb_4bit_use_double_quant: bool = False,
            **_kwargs,
        ):
            self.load_in_4bit = load_in_4bit
            self.llm_int8_enable_fp32_cpu_offload = llm_int8_enable_fp32_cpu_offload
            self.bnb_4bit_compute_dtype = bnb_4bit_compute_dtype
            self.bnb_4bit_quant_type = bnb_4bit_quant_type
            self.bnb_4bit_use_double_quant = bnb_4bit_use_double_quant

    class FakeAutoProcessor:
        @staticmethod
        def from_pretrained(model_id: str):
            captured["processor_model_id"] = model_id
            return object()

    class FakeModel:
        def __init__(self):
            self.moved_to: str | None = None
            self.device = "cpu"

        def to(self, device: str, dtype=None):
            self.moved_to = device
            self.device = device
            return self

    class FakeAutoModel:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs):
            captured["model_model_id"] = model_id
            captured.update(kwargs)
            return FakeModel()

    fake_transformers = types.SimpleNamespace(
        BitsAndBytesConfig=FakeBitsAndBytesConfig,
        AutoProcessor=FakeAutoProcessor,
        AutoModelForImageTextToText=FakeAutoModel,
    )

    fake_torch = types.SimpleNamespace(bfloat16=object(), float16=object())
    fake_cuda = types.SimpleNamespace(is_available=lambda: True, is_bf16_supported=lambda: True)
    fake_torch.cuda = fake_cuda

    monkeypatch.setattr(medgemma, "_lazy_import_transformers", lambda: fake_transformers)
    monkeypatch.setattr(medgemma, "_lazy_import_torch", lambda: fake_torch)
    monkeypatch.setattr(medgemma.importlib.util, "find_spec", lambda _name: object())

    model, _processor = medgemma.load_model("local/path", device_map="auto")

    q = captured.get("quantization_config")
    assert isinstance(q, FakeBitsAndBytesConfig)
    assert q.load_in_4bit is True
    assert q.llm_int8_enable_fp32_cpu_offload is True
    assert q.bnb_4bit_use_double_quant is True
    assert q.bnb_4bit_quant_type == "nf4"
    assert captured.get("device_map") is None
    assert getattr(model, "moved_to") == "cuda"
