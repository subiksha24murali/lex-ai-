import tempfile


_whisper_model = None


def _get_whisper_model():
    global _whisper_model

    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model("base")
    return _whisper_model


def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe an audio file with the CPU-friendly Whisper base model."""
    result = _get_whisper_model().transcribe(audio_file_path)
    return result["text"].strip()


def speak_text(text: str, language: str) -> str:
    """Generate an MP3 speech file using gTTS and return its path."""
    if language not in {"en", "hi", "ta"}:
        raise ValueError("Unsupported speech language. Use en, hi, or ta.")

    from gtts import gTTS

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        audio_path = audio_file.name

    gTTS(text=text, lang=language).save(audio_path)
    return audio_path