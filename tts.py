# Turns text into an audio file via Google Cloud TTS.
#
# Does not play the audio — that belongs to player.py. Keeping them apart
# lets the synthesis and playback times be measured separately.

from google.cloud import texttospeech
from google.api_core import client_options as client_options_lib
from google.api_core.exceptions import GoogleAPIError

from config import (
    GOOGLE_TTS_API_KEY,
    GOOGLE_TTS_VOICE,
    TTS_LANGUAGE_CODE,
    TTS_OUTPUT_FILE,
    mask_secrets,
    require_key,
)

# Built once on first use and reused.
_client = None


def _get_client() -> texttospeech.TextToSpeechClient:
    """Return the TTS client, creating it on first call.

    Raises:
        ValueError: if the API key is not set.
    """
    global _client

    if _client is None:
        options = client_options_lib.ClientOptions(
            api_key=require_key("GOOGLE_TTS_API_KEY", GOOGLE_TTS_API_KEY)
        )
        _client = texttospeech.TextToSpeechClient(client_options=options)

    return _client


def synthesize_speech(text: str) -> str:
    """Synthesise the text in the active language and write it to disk.

    Returns:
        Path to the generated audio file.

    Raises:
        ValueError: if the key is missing.
        ConnectionError: on API or network failures.
        RuntimeError: on anything unexpected.
    """
    client = _get_client()

    voice = texttospeech.VoiceSelectionParams(
        language_code=TTS_LANGUAGE_CODE,
        name=GOOGLE_TTS_VOICE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=1.0,
    )

    try:
        response = client.synthesize_speech(
            request={
                "input": texttospeech.SynthesisInput(text=text),
                "voice": voice,
                "audio_config": audio_config,
            }
        )
    except GoogleAPIError as e:
        raise _explain_api_error(e) from e
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ("connection", "network", "timeout", "unreachable")):
            raise ConnectionError(
                "Hata: Google Cloud TTS için internet bağlantısı kurulamadı.\n"
                "Bağlantını kontrol edip tekrar dene."
            ) from e
        raise RuntimeError(
            f"Hata: Beklenmedik TTS hatası.\nDetay: {mask_secrets(e)}"
        ) from e

    with open(TTS_OUTPUT_FILE, "wb") as out:
        out.write(response.audio_content)

    return TTS_OUTPUT_FILE


def _explain_api_error(error: GoogleAPIError) -> Exception:
    """Translate a Cloud TTS error into one that tells the user what to do."""
    err = str(error).lower()

    if any(k in err for k in ("api key", "permission", "unauthenticated")):
        return ConnectionError(
            "Hata: Google Cloud TTS API anahtarı geçersiz veya yetkisi yok.\n"
            ".env dosyasındaki GOOGLE_TTS_API_KEY değerini ve Cloud Console'da "
            "Text-to-Speech API'nin etkin olduğunu kontrol et."
        )

    if any(k in err for k in ("quota", "resource_exhausted", "rate limit", "429")):
        return ConnectionError(
            "Hata: Google Cloud TTS kullanım kotası aşıldı.\n"
            "Google Cloud Console'dan kota durumunu kontrol et."
        )

    # Unrecognised: show the raw text, but mask the key first.
    return ConnectionError(
        f"Hata: Google Cloud TTS API hatası.\nDetay: {mask_secrets(error)}"
    )
