import importlib
import importlib.util
import json
import re
import threading
from typing import Any

DEFAULT_MODEL_ID = "google/medgemma-4b-it"

_MODEL: Any | None = None
_TOKENIZER: Any | None = None
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
    """Load tokenizer + model.

    Uses 4-bit quantization (BitsAndBytesConfig(load_in_4bit=True)) when
    transformers and bitsandbytes are available.
    """

    global _MODEL, _TOKENIZER, _MODEL_ID

    with _LOAD_LOCK:
        if _MODEL is not None and _TOKENIZER is not None and _MODEL_ID == model_id:
            return _MODEL, _TOKENIZER

        transformers = _lazy_import_transformers()
        _lazy_import_torch()

        quantization_config = None
        bnb_cls = getattr(transformers, "BitsAndBytesConfig", None)
        if bnb_cls is not None and importlib.util.find_spec("bitsandbytes") is not None:
            try:
                quantization_config = bnb_cls(load_in_4bit=True)
            except Exception:
                quantization_config = None

        tokenizer = transformers.AutoTokenizer.from_pretrained(model_id)

        model = transformers.AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map=device_map,
            quantization_config=quantization_config,
        )
        try:
            model.eval()
        except Exception:
            pass

        _MODEL = model
        _TOKENIZER = tokenizer
        _MODEL_ID = model_id
        return model, tokenizer


def _render_prompt(tokenizer: Any, prompt: str) -> dict[str, Any]:
    if hasattr(tokenizer, "apply_chat_template"):
        messages = [{"role": "user", "content": prompt}]
        try:
            out = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            if isinstance(out, dict) and "input_ids" in out:
                return {
                    "input_ids": out["input_ids"],
                    "attention_mask": out.get("attention_mask"),
                }
        except TypeError:
            pass

        input_ids = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
        )
        return {"input_ids": input_ids, "attention_mask": None}

    enc = tokenizer(prompt, return_tensors="pt")
    return {"input_ids": enc["input_ids"], "attention_mask": enc.get("attention_mask")}


def _decode_generated(tokenizer: Any, input_ids: Any, output_ids: Any) -> str:
    try:
        # Common HF pattern: output includes the prompt prefix.
        gen_only = output_ids[0][input_ids.shape[-1] :]
        return tokenizer.decode(gen_only, skip_special_tokens=True)
    except Exception:
        return tokenizer.decode(output_ids[0], skip_special_tokens=True)


def generate(prompt: str, *, max_new_tokens: int, temperature: float) -> str:
    """Generate a response and return a valid JSON string.

    If JSON extraction/parsing fails, retries up to 2 times with a repair prompt.
    """

    global _MODEL, _TOKENIZER

    if _MODEL is None or _TOKENIZER is None:
        load_model(DEFAULT_MODEL_ID)

    assert _MODEL is not None
    assert _TOKENIZER is not None

    def _one_shot(p: str, *, temp: float) -> str:
        torch = _lazy_import_torch()

        inputs = _render_prompt(_TOKENIZER, p)
        if inputs.get("attention_mask") is None:
            inputs["attention_mask"] = torch.ones_like(inputs["input_ids"])

        if hasattr(_MODEL, "device"):
            for k, v in list(inputs.items()):
                if hasattr(v, "to"):
                    inputs[k] = v.to(_MODEL.device)

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
        }
        if temp and temp > 0:
            gen_kwargs.update({"do_sample": True, "temperature": temp})

        with torch.inference_mode():
            output_ids = _MODEL.generate(**inputs, **gen_kwargs)

        return _decode_generated(_TOKENIZER, inputs["input_ids"], output_ids)

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
