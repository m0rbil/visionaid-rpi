# Turns an image into a spoken-language description via Gemini.
#
# Takes an image object and does not know where it came from — the camera or
# the disk — which keeps this module testable without hardware.

from google import genai
from google.genai import types
from PIL import Image

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_THINKING_BUDGET,
    VISION_PROMPT,
    mask_secrets,
    require_key,
)

# Built once on first use and reused; rebuilding per photo wastes time.
_client = None

_REQUEST_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=GEMINI_THINKING_BUDGET)
)


def _get_client() -> genai.Client:
    """Return the Gemini client, creating it on first call.

    Raises:
        ValueError: if the API key is not set.
    """
    global _client

    if _client is None:
        _client = genai.Client(api_key=require_key("GEMINI_API_KEY", GEMINI_API_KEY))

    return _client


def describe_image(image: Image.Image) -> str:
    """Describe the given image in the active language.

    Raises:
        ValueError: if the key is missing or the response is unusable.
        ConnectionError: on API or network failures.
    """
    client = _get_client()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[VISION_PROMPT, image],
            config=_REQUEST_CONFIG,
        )
        # .text is None when the response was blocked.
        description = (response.text or "").strip()
    except Exception as e:
        raise _explain_api_error(e) from e

    if not description:
        raise ValueError(
            "Hata: Gemini boş yanıt döndürdü.\n"
            "Fotoğraf güvenlik filtresine takılmış olabilir; farklı bir "
            "fotoğrafla tekrar dene."
        )

    return description


def _explain_api_error(error: Exception) -> Exception:
    """Translate an API error into one that tells the user what to do.

    The keywords are deliberately narrow. Matching something broad like
    "invalid" would blame the API key for unrelated failures and send the
    user chasing the wrong problem.
    """
    err = str(error).lower()

    if any(k in err for k in ("api_key", "api key", "credential", "unauthenticated")):
        return ConnectionError(
            "Hata: API anahtarı geçersiz veya hatalı.\n"
            ".env dosyasındaki GEMINI_API_KEY değerini kontrol et."
        )

    if any(k in err for k in ("quota", "rate limit", "resource_exhausted", "429")):
        return ConnectionError(
            "Hata: API istek limitine ulaşıldı.\n"
            "Birkaç dakika bekleyip tekrar dene (ücretsiz tier: dakikada 15 istek)."
        )

    if any(k in err for k in ("network", "connection", "timeout", "unreachable")):
        return ConnectionError(
            "Hata: İnternet bağlantısı kurulamadı.\n"
            "Bağlantını kontrol edip tekrar dene."
        )

    if any(k in err for k in ("safety", "blocked", "finish_reason")):
        return ValueError(
            "Hata: Bu fotoğraf Gemini'nin güvenlik filtresine takıldı.\n"
            "Farklı bir fotoğraf dene."
        )

    # Unrecognised: show the raw text, but mask the key first.
    return ConnectionError(
        f"Hata: Gemini API'den beklenmedik yanıt alındı.\n"
        f"Detay: {mask_secrets(error)}"
    )
