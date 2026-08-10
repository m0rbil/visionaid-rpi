# tts.py - Metinden Sese Dönüştürme (Google Cloud TTS - Chirp3 HD)
# -----------------------------------------------
# Bu modülün tek işi: verilen metni ses dosyasına çevirmek.
# Sesi ÇALMAZ — o iş player.py'ye ait. Bu ayrım sayesinde "ses üretme"
# ve "ses çalma" sürelerini ayrı ayrı ölçebiliyoruz.

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

# İstemci ilk kullanımda oluşturulup saklanır (her seferinde kurmak yavaş).
_client = None


def _get_client() -> texttospeech.TextToSpeechClient:
    """
    Google Cloud TTS istemcisini hazırlar. İlk çağrıda kurar, sonra aynısını verir.

    Raises:
        ValueError: API anahtarı tanımlı değilse
    """
    global _client

    if _client is None:
        options = client_options_lib.ClientOptions(
            api_key=require_key("GOOGLE_TTS_API_KEY", GOOGLE_TTS_API_KEY)
        )
        _client = texttospeech.TextToSpeechClient(client_options=options)

    return _client


def synthesize_speech(text: str) -> str:
    """
    Metni aktif dildeki sese çevirir ve ses dosyası olarak diske yazar.

    Ses formatı olarak sıkıştırılmamış WAV (LINEAR16) kullanılır: MP3'e göre
    belirgin daha kaliteli, karşılığında dosya daha büyük.

    Args:
        text: Seslendirilecek Türkçe metin

    Returns:
        Oluşturulan ses dosyasının yolu

    Raises:
        ValueError: Anahtar eksikse
        ConnectionError: API veya ağ kaynaklı sorunlarda
        RuntimeError: Beklenmedik durumlarda
    """
    client = _get_client()

    # Dil kodu ve ses adı config'teki aktif dil paketinden gelir.
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
        # 'from e': asıl hatayı bu hatanın altına iliştirir, iz kaybolmaz.
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
    """
    Cloud TTS'ten gelen teknik hatayı, kullanıcının ne yapması gerektiğini
    söyleyen bir hataya çevirir.
    """
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

    # Tanınmayan hata: ham metni gösteriyoruz, ama önce anahtarı gizliyoruz.
    return ConnectionError(
        f"Hata: Google Cloud TTS API hatası.\nDetay: {mask_secrets(error)}"
    )
