# All project settings live here.
#
# This file contains no secrets. API keys are read from .env, which is
# gitignored. Copy .env.example to .env and fill in your own keys.

import os
import re

from dotenv import load_dotenv

load_dotenv()


# ── Secrets (read from .env) ────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY", "")


def require_key(name: str, value: str) -> str:
    """Return the key, or fail with instructions if it is not set.

    Raises:
        ValueError: if the key is missing.
    """
    if not value:
        raise ValueError(
            f"Hata: '{name}' tanımlı değil.\n"
            ".env.example dosyasını .env olarak kopyala ve içine kendi "
            "anahtarını yaz.\n"
            "Anahtar almak için: https://console.cloud.google.com/apis/credentials"
        )
    return value


def mask_secrets(text: str) -> str:
    """Replace any API key found in the text with '***'.

    Google client libraries sometimes embed the full request URL in error
    messages, and the API key travels in that URL as '?key=AIza...'. Printing
    such an error verbatim would expose the key in terminal output and
    screenshots.
    """
    safe = str(text)

    for key in (GEMINI_API_KEY, GOOGLE_TTS_API_KEY):
        if key:
            safe = safe.replace(key, "***")

    # Catch any remaining string shaped like a Google API key.
    return re.sub(r"AIza[0-9A-Za-z_\-]{35}", "***", safe)


# ── Gemini (vision) ─────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"

# Internal reasoning budget. 0 disables it.
#
# Gemini 2.5 models reason before answering, which helps on multi-step
# problems and is wasted on single-step image description. Measured on the
# same image, 4 runs each: enabled 11.80 s, disabled 1.87 s (84% faster),
# with no observable difference in description quality.
GEMINI_THINKING_BUDGET = 0


# ── Language packs ──────────────────────────────────────────────────────────
#
# Each supported language ships its own prompt and TTS voice.
#
# The prompts are written separately rather than translated by the model.
# The positional phrasings ("tam önünüzde" / "directly ahead of you") carry
# the safety information; leaving their wording to the model risks turning a
# warning in one language into a plain description in another.

_TR_PROMPT = (
    "Sen görme engelli bir kişinin gözlerisin. Onun yerine bu fotoğrafa bakıyorsun "
    "ve ona en faydalı, en somut bilgiyi Türkçe olarak aktaracaksın.\n\n"

    "Önce fotoğrafın hangi türde olduğuna karar ver, sonra ilgili kurala göre yanıt ver:\n\n"

    "1) YOL, KALDIRIM, MEKÂN veya DIŞ/İÇ ORTAM ise:\n"
    "- İlk cümlede nerede olunduğunu söyle (örnek: kalabalık bir cadde, dar bir koridor, bir oda).\n"
    "- İkinci cümlede MUTLAKA şunu yap: önde veya yakında bulunan EN ÖNEMLİ 1-2 engeli, "
    "tehlikeyi veya nesneyi, KONUMUYLA birlikte söyle. Konum için şu kalıpları kullan: "
    "'tam önünüzde', 'sağınızda', 'solunuzda', 'birkaç adım ilerde'. "
    "Engel örnekleri: basamak, merdiven, araç, bisiklet, kalabalık, dar geçit, çukur, direk.\n"
    "- Eğer net bir engel yoksa, bunun yerine yürünebilir bir yön veya boş alan belirt "
    "(örnek: 'önünüz açık, düz ilerleyebilirsiniz').\n"
    "- Bu kategori için yanıt ASLA sadece tasvirden ibaret olmasın, MUTLAKA bir "
    "konum/yön/güvenlik bilgisi içersin.\n"
    "- Toplam 2-3 cümleyi geçme.\n\n"

    "2) Tek bir NESNE, ÜRÜN veya YAZI ise:\n"
    "- Nesnenin ne olduğunu ve ne işe yaradığını 1-2 cümleyle açıkla.\n"
    "- Üzerinde yazı, fiyat, tarih veya miktar varsa aynen oku.\n\n"

    "3) Bir KİŞİ veya SOSYAL ORTAM ise:\n"
    "- Ortamı ve yaklaşık kaç kişi olduğunu kısaca belirt.\n"
    "- Kullanıcıyı ilgilendirebilecek bir durum varsa (örnek: biri ona doğru geliyor, "
    "biri elini uzatmış) belirt.\n"
    "- 2 cümleyi geçme.\n\n"

    "4) Fotoğraf çok bulanık, karanlık veya anlaşılmazsa:\n"
    "- Tahmin yürütme. Bunun yerine net şekilde söyle: "
    "'Görüntü net değil, kamerayı yeniden doğrultup tekrar deneyin.'\n\n"

    "Genel kurallar:\n"
    "- Sade, kısa cümleler kullan; sesli okunacağını unutma.\n"
    "- Gereksiz sıfat ve süsleme yapma, doğrudan ve pratik ol.\n"
    "- Gerçekten tehlikeli bir durum varsa (gelen araç, merdiven boşluğu, ani yükseklik "
    "farkı) cümleye 'Dikkat,' diyerek başla."
)

_EN_PROMPT = (
    "You are the eyes of a person who is blind. You are looking at this photo on "
    "their behalf and will give them the most useful, most concrete information "
    "in English.\n\n"

    "First decide what kind of photo this is, then answer according to the "
    "matching rule:\n\n"

    "1) A ROAD, SIDEWALK, PLACE or INDOOR/OUTDOOR SETTING:\n"
    "- In the first sentence, say where they are (example: a busy street, a narrow "
    "corridor, a room).\n"
    "- In the second sentence you MUST do this: name the 1-2 most important "
    "obstacles, hazards or objects ahead or nearby, together with their POSITION. "
    "Use these phrasings for position: 'directly ahead of you', 'to your right', "
    "'to your left', 'a few steps ahead'. "
    "Obstacle examples: a step, stairs, a vehicle, a bicycle, a crowd, a narrow "
    "gap, a hole, a pole.\n"
    "- If there is no clear obstacle, state a walkable direction or open space "
    "instead (example: 'the way ahead is clear, you can walk straight on').\n"
    "- For this category the answer must NEVER be description alone; it MUST "
    "contain position, direction or safety information.\n"
    "- Do not exceed 2-3 sentences in total.\n\n"

    "2) A single OBJECT, PRODUCT or piece of TEXT:\n"
    "- Explain what the object is and what it is used for in 1-2 sentences.\n"
    "- If there is any text, price, date or quantity on it, read it out exactly.\n\n"

    "3) A PERSON or SOCIAL SETTING:\n"
    "- Briefly state the setting and roughly how many people are present.\n"
    "- Mention anything that may concern the user (example: someone is walking "
    "towards them, someone is holding out their hand).\n"
    "- Do not exceed 2 sentences.\n\n"

    "4) If the photo is very blurry, dark or unintelligible:\n"
    "- Do not guess. Instead say clearly: "
    "'The image is not clear, please point the camera again and try once more.'\n\n"

    "General rules:\n"
    "- Use plain, short sentences; remember this will be read aloud.\n"
    "- Avoid unnecessary adjectives and embellishment, be direct and practical.\n"
    "- If there is a genuinely dangerous situation (an approaching vehicle, a "
    "stairwell drop, a sudden change in height) begin the sentence with 'Careful,'."
)

# Voice names verified against https://cloud.google.com/text-to-speech/docs/voices
LANGUAGES = {
    "tr": {
        "prompt": _TR_PROMPT,
        "voice": "tr-TR-Chirp3-HD-Achernar",
        "language_code": "tr-TR",
    },
    "en": {
        "prompt": _EN_PROMPT,
        "voice": "en-US-Chirp3-HD-Achernar",
        "language_code": "en-US",
    },
}

ACTIVE_LANGUAGE = os.getenv("VISIONAID_LANG", "tr").strip().lower()

if ACTIVE_LANGUAGE not in LANGUAGES:
    raise ValueError(
        f"Hata: '{ACTIVE_LANGUAGE}' desteklenen bir dil değil.\n"
        f"Kullanılabilir diller: {', '.join(sorted(LANGUAGES))}\n"
        ".env dosyasındaki VISIONAID_LANG değerini düzelt."
    )

_active = LANGUAGES[ACTIVE_LANGUAGE]

# Other modules read these; they never need to know which language is active.
VISION_PROMPT = _active["prompt"]


# ── Speech (Google Cloud TTS, Chirp3-HD) ────────────────────────────────────

GOOGLE_TTS_VOICE = _active["voice"]
TTS_LANGUAGE_CODE = _active["language_code"]

# Uncompressed WAV: clearly better quality than MP3 from the same voice.
# The larger download is a deliberate trade-off.
TTS_OUTPUT_FILE = "output.wav"


# ── Raspberry Pi hardware ───────────────────────────────────────────────────

# Button wiring: pin 11 (GPIO 17, BCM) to one leg, pin 6 (GND) to the other.
GPIO_BUTTON_PIN = 17

# Full HD so the model can resolve small details such as sign text or the
# edge of a step.
CAMERA_RESOLUTION = (1920, 1080)

# Time given to auto-exposure and white balance before capturing. Without it
# the frame comes out blurry or dark and the description becomes useless.
CAMERA_WARMUP_SECONDS = 1.5


# ── Test mode ───────────────────────────────────────────────────────────────

# Used instead of the camera when picamera2 is unavailable.
TEST_IMAGE_PATH = "test.jpg"
