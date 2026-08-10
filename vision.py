# vision.py - Gemini API ile Görüntü Betimleme
# -----------------------------------------------
# Bu modülün tek işi: elindeki fotoğrafı Gemini'ye gönderip Türkçe
# betimleme metnini almak. Fotoğrafın nereden geldiğini bilmez —
# kameradan da gelmiş olabilir, diskten de. Bu ayrım sayesinde kamera
# olmadan da test edilebilir.

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

# İstemci ilk kullanımda oluşturulup burada saklanır.
# Her fotoğrafta yeniden kurmak gereksiz zaman kaybı olurdu.
_client = None

# İstek ayarları bir kez hazırlanır, her çağrıda yeniden kurulmaz.
_REQUEST_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=GEMINI_THINKING_BUDGET)
)


def _get_client() -> genai.Client:
    """
    Gemini istemcisini hazırlar. İlk çağrıda kurar, sonrakilerde aynısını verir.

    Raises:
        ValueError: API anahtarı tanımlı değilse
    """
    global _client

    if _client is None:
        _client = genai.Client(api_key=require_key("GEMINI_API_KEY", GEMINI_API_KEY))

    return _client


def describe_image(image: Image.Image) -> str:
    """
    Verilen fotoğrafı Gemini'ye gönderir ve Türkçe betimlemeyi döndürür.

    Args:
        image: Betimlenecek fotoğraf (PIL Image nesnesi)

    Returns:
        Türkçe betimleme metni

    Raises:
        ValueError: Anahtar eksikse veya yanıt kullanılamazsa
        ConnectionError: API veya ağ kaynaklı sorunlarda
    """
    client = _get_client()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[VISION_PROMPT, image],
            config=_REQUEST_CONFIG,
        )
        # Yanıt engellendiyse .text None olur; bu yüzden önce boşa çeviriyoruz.
        description = (response.text or "").strip()
    except Exception as e:
        # 'from e': asıl hatayı bu hatanın altına iliştirir. Sorun ararken
        # hatanın nereden kaynaklandığı kaybolmaz.
        raise _explain_api_error(e) from e

    if not description:
        raise ValueError(
            "Hata: Gemini boş yanıt döndürdü.\n"
            "Fotoğraf güvenlik filtresine takılmış olabilir; farklı bir "
            "fotoğrafla tekrar dene."
        )

    return description


def _explain_api_error(error: Exception) -> Exception:
    """
    Gemini'den gelen teknik hatayı, kullanıcının anlayacağı ve ne yapması
    gerektiğini söyleyen bir hataya çevirir.

    Aranan kelimeler bilinçli olarak dardır. Örneğin sadece "invalid"
    aransaydı, anahtarla hiç ilgisi olmayan hatalarda da kullanıcıya
    "anahtarın geçersiz" denir ve boşuna anahtarla uğraşırdı.

    Args:
        error: API'den gelen özgün hata

    Returns:
        Fırlatılmaya hazır, açıklayıcı hata nesnesi
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

    # Tanınmayan hata: ham metni gösteriyoruz, ama önce anahtarı gizliyoruz.
    return ConnectionError(
        f"Hata: Gemini API'den beklenmedik yanıt alındı.\n"
        f"Detay: {mask_secrets(error)}"
    )
