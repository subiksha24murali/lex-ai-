"""Translation backends for Google Translate and AI4Bharat IndicTrans2."""
from typing import Any

from src.config import SUPPORTED_LANGUAGES, TRANSLATION_BACKEND


INDICTRANS2_MODEL = "ai4bharat/indictrans2-en-indic-1B"
INDICTRANS2_LANGUAGE_CODES = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "ta": "tam_Taml",
}

_indictrans2_tokenizer: Any = None
_indictrans2_model: Any = None
_indictrans2_processor: Any = None
_indictrans2_device: Any = None


def _load_indictrans2():
    """Load IndicTrans2 once per process, only when that backend is selected."""
    global _indictrans2_tokenizer, _indictrans2_model, _indictrans2_processor, _indictrans2_device

    if _indictrans2_model is None:
        import torch
        from IndicTransToolkit import IndicProcessor
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        _indictrans2_device = "cuda" if torch.cuda.is_available() else "cpu"
        _indictrans2_tokenizer = AutoTokenizer.from_pretrained(
            INDICTRANS2_MODEL,
            trust_remote_code=True,
        )
        _indictrans2_model = AutoModelForSeq2SeqLM.from_pretrained(
            INDICTRANS2_MODEL,
            trust_remote_code=True,
        ).to(_indictrans2_device)
        _indictrans2_processor = IndicProcessor(inference=True)

    return (
        _indictrans2_tokenizer,
        _indictrans2_model,
        _indictrans2_processor,
        _indictrans2_device,
    )


def translate_text_indictrans2(text: str, target_lang: str) -> str:
    """Translate English text to Hindi or Tamil with IndicTrans2."""
    target_code = INDICTRANS2_LANGUAGE_CODES.get(target_lang)
    if target_code is None:
        raise ValueError(
            f"IndicTrans2 supports these target language codes: "
            f"{list(INDICTRANS2_LANGUAGE_CODES)}"
        )
    if target_lang == "en":
        return text

    import torch

    tokenizer, model, processor, device = _load_indictrans2()
    batch = processor.preprocess_batch(
        [text],
        src_lang=INDICTRANS2_LANGUAGE_CODES["en"],
        tgt_lang=target_code,
    )
    inputs = tokenizer(
        batch,
        truncation=True,
        padding="longest",
        return_tensors="pt",
        return_attention_mask=True,
    ).to(device)

    with torch.inference_mode():
        generated_tokens = model.generate(
            **inputs,
            use_cache=True,
            min_length=0,
            max_length=256,
            num_beams=5,
            num_return_sequences=1,
        )

    decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
    return processor.postprocess_batch(decoded, lang=target_code)[0]


def translate_text(text: str, target_lang: str) -> str:
    """target_lang: one of the keys in SUPPORTED_LANGUAGES ('en', 'hi', 'ta')."""
    if target_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language code: {target_lang}. "
            f"Supported: {list(SUPPORTED_LANGUAGES)}"
        )
    if target_lang == "en":
        return text

    if TRANSLATION_BACKEND == "indictrans2":
        return translate_text_indictrans2(text, target_lang)
    if TRANSLATION_BACKEND != "google":
        raise ValueError(
            f"Unsupported translation backend: {TRANSLATION_BACKEND}. "
            "Supported: google, indictrans2"
        )

    from deep_translator import GoogleTranslator

    return GoogleTranslator(source="auto", target=target_lang).translate(text)


def detect_and_translate_to_english(text: str) -> str:
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source="auto", target="en").translate(text)
