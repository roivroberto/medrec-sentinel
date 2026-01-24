import importlib
import importlib.util
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

HF_MODEL_ID = "google/medgemma-4b-it"


def default_model_id() -> str:
    """Return a default model id/path.

    Priority:
    1) MEDGEMMA_MODEL_ID / MEDGEMMA_MODEL_PATH env var
    2) local snapshot under <repo>/models/google__medgemma-4b-it
    3) Hugging Face repo id (HF_MODEL_ID)
    """

    env = os.environ.get("MEDGEMMA_MODEL_ID") or os.environ.get("MEDGEMMA_MODEL_PATH")
    if env:
        return env

    repo_root = Path(__file__).resolve().parents[2]
    local = repo_root / "models" / "google__medgemma-4b-it"
    if local.exists():
        return str(local)

    return HF_MODEL_ID

_MODEL: Any | None = None
_PROCESSOR: Any | None = None
_MODEL_ID: str | None = None

_LOAD_LOCK = threading.Lock()


def extract_json_block(text: str) -> str:
    """Extract the first JSON object found in a markdown fenced block.

    Prefers ```json fenced blocks but will fall back to any ``` fenced block.
    Returns the raw JSON string (stripped). Raises ValueError if none found.
    """

    def _first_parseable_from_fences(pattern: str) -> str | None:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            candidate = m.group(1).strip()
            if not candidate:
                continue

            try:
                json.loads(candidate)
            except Exception:
                continue
            return candidate
        return None

    for pat in (r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"):
        candidate = _first_parseable_from_fences(pat)
        if candidate is not None:
            return candidate

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            _obj, end = decoder.raw_decode(text[idx:])
        except Exception:
            continue
        return text[idx : idx + end].strip()

    raise ValueError("No JSON block found")


def _lazy_import_transformers() -> Any:
    try:
        return importlib.import_module("transformers")
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "transformers is required for MedGemma model loading/generation"
        ) from e


def _lazy_import_torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("torch is required for MedGemma generation") from e


def load_model(model_id: str, device_map: str = "auto"):
    """Load processor + model.

    Uses 4-bit quantization (BitsAndBytesConfig(load_in_4bit=True)) when
    transformers and bitsandbytes are available.
    """

    global _MODEL, _PROCESSOR, _MODEL_ID

    with _LOAD_LOCK:
        if _MODEL is not None and _PROCESSOR is not None and _MODEL_ID == model_id:
            return _MODEL, _PROCESSOR

        transformers = _lazy_import_transformers()
        torch = _lazy_import_torch()

        quantization_config = None
        bnb_cls = getattr(transformers, "BitsAndBytesConfig", None)
        if bnb_cls is not None and importlib.util.find_spec("bitsandbytes") is not None:
            try:
                # Prefer a memory-efficient 4-bit config so the model is more
                # likely to fit on consumer GPUs; allow CPU offload if needed.
                bnb_compute_dtype = torch.float16
                if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
                    bnb_compute_dtype = torch.bfloat16

                quantization_config = bnb_cls(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=bnb_compute_dtype,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    llm_int8_enable_fp32_cpu_offload=True,
                )
            except Exception:
                quantization_config = None

        processor = transformers.AutoProcessor.from_pretrained(model_id)

        torch_dtype = torch.bfloat16
        if torch.cuda.is_available() and not torch.cuda.is_bf16_supported():
            torch_dtype = torch.float16

        model_kwargs: dict[str, Any] = {
            "torch_dtype": torch_dtype,
            "quantization_config": quantization_config,
        }

        use_cuda = False
        if quantization_config is None:
            # Non-quantized loads rely on Accelerate's device_map/offload.
            model_kwargs["device_map"] = device_map
        else:
            # bitsandbytes + accelerate dispatch can be fragile on some setups.
            # Prefer a single-device load and then move the model to CUDA.
            use_cuda = torch.cuda.is_available() and (device_map or "auto") != "cpu"

        model = transformers.AutoModelForImageTextToText.from_pretrained(
            model_id,
            **model_kwargs,
        )

        if use_cuda and hasattr(model, "to"):
            try:
                model = model.to("cuda")
            except Exception as e:
                # If the quantized model still doesn't fit, keep it on CPU.
                msg = str(e).lower()
                if "out of memory" not in msg:
                    raise
        try:
            model.eval()
        except Exception:
            pass

        _MODEL = model
        _PROCESSOR = processor
        _MODEL_ID = model_id
        return model, processor


def _render_prompt(processor: Any, prompt: str) -> Any:
    if hasattr(processor, "apply_chat_template"):
        # MedGemma expects a list of chat messages whose content is a list of
        # typed segments.
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ]
        try:
            out = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
            if isinstance(out, dict) and "input_ids" in out:
                return out
        except Exception:
            pass

    return processor(text=prompt, return_tensors="pt")


def _decode_generated(processor: Any, input_ids: Any, output_ids: Any) -> str:
    try:
        # Common HF pattern: output includes the prompt prefix.
        gen_only = output_ids[0][input_ids.shape[-1] :]
        return processor.decode(gen_only, skip_special_tokens=True)
    except Exception:
        return processor.decode(output_ids[0], skip_special_tokens=True)


def generate(prompt: str, *, max_new_tokens: int, temperature: float) -> str:
    """Generate a response and return a valid JSON string.

    If JSON extraction/parsing fails, retries up to 2 times with a repair prompt.
    """

    global _MODEL, _PROCESSOR

    if _MODEL is None or _PROCESSOR is None:
        device_map = os.environ.get("MEDGEMMA_DEVICE_MAP", "auto")
        load_model(default_model_id(), device_map=device_map)

    model: Any = _MODEL
    processor: Any = _PROCESSOR
    assert model is not None
    assert processor is not None

    def _one_shot(p: str, *, temp: float) -> str:
        torch = _lazy_import_torch()

        inputs: Any = _render_prompt(processor, p)
        if inputs.get("attention_mask") is None and inputs.get("input_ids") is not None:
            inputs["attention_mask"] = torch.ones_like(inputs["input_ids"])

        input_len = inputs["input_ids"].shape[-1]

        if hasattr(inputs, "to") and hasattr(model, "device"):
            try:
                inputs = inputs.to(model.device, dtype=getattr(model, "dtype", None))
            except Exception:
                inputs = inputs.to(model.device)
        elif hasattr(model, "device"):
            for k, v in list(inputs.items()):
                if hasattr(v, "to"):
                    inputs[k] = v.to(model.device)

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
        }
        if temp and temp > 0:
            gen_kwargs.update({"do_sample": True, "temperature": temp})

        with torch.inference_mode():
            output_ids = model.generate(**inputs, **gen_kwargs)

        # slice off the prompt prefix for cleaner decoding
        try:
            gen_only = output_ids[0][input_len:]
            return processor.decode(gen_only, skip_special_tokens=True)
        except Exception:
            return _decode_generated(processor, inputs["input_ids"], output_ids)

    last_text = _one_shot(prompt, temp=temperature)
    for attempt in range(3):
        try:
            json_str = extract_json_block(last_text)
            json.loads(json_str)
            return json_str
        except Exception:
            if attempt >= 2:
                break

            repair_prompt = (
                "Repair the JSON from the previous response. Output ONLY valid JSON "
                "in a ```json fenced block with no extra text.\n\n"
                "Previous response:\n"
                f"{last_text}"
            )
            last_text = _one_shot(repair_prompt, temp=0.0)

    raise ValueError("Model output did not contain valid JSON")
