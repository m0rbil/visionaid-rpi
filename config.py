# config.py - VisionAid Ayarları
# -----------------------------------------------
# Projenin tüm ayarları bu dosyada toplanır.
#
# ÖNEMLİ: Bu dosya GİZLİ BİLGİ İÇERMEZ.
# API anahtarları .env dosyasından okunur; .env ise GitHub'a gönderilmez.
# Kurulum için .env.example dosyasını kopyalayıp kendi anahtarlarını yaz.

import os
import re

from dotenv import load_dotenv

# .env dosyasındaki değerleri ortam değişkeni olarak yükler.
# Dosya yoksa hata vermez, değerler boş kalır (aşağıda kontrol ediliyor).
load_dotenv()


# ── Gizli Anahtarlar (.env dosyasından okunur) ──────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY", "")


def require_key(name: str, value: str) -> str:
    """
    Bir anahtarın gerçekten tanımlı olduğunu doğrular.

    Anahtar eksikse program sessizce yanlış çalışmak yerine burada durur ve
    kullanıcıya ne yapması gerektiğini söyler.

    Args:
        name: Anahtarın .env içindeki adı (hata mesajında gösterilir)
        value: Okunan değer

    Returns:
        Geçerli anahtar değeri

    Raises:
        ValueError: Anahtar tanımlı değilse
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
    """
    Metin içinde geçen API anahtarlarını gizler.

    Neden gerekli: Google'ın kütüphaneleri hata mesajlarına bazen isteğin
    tam adresini ekler; anahtar o adresin içinde ('?key=AIza...') geçer.
    Hata mesajını olduğu gibi ekrana bastığımızda anahtar da görünür olurdu
    ve paylaşılan bir ekran görüntüsüyle başkasının eline geçebilirdi.

    Bu fonksiyon anahtarı '***' ile değiştirir; mesajın kalanı bozulmaz.

    Args:
        text: Ekrana basılacak ham hata metni

    Returns:
        Anahtarları gizlenmiş metin
    """
    safe = str(text)

    # 1) Kendi anahtarlarımız metinde birebir geçiyorsa temizle
    for key in (GEMINI_API_KEY, GOOGLE_TTS_API_KEY):
        if key:
            safe = safe.replace(key, "***")

    # 2) Google anahtar biçimine uyan başka bir dizi kaldıysa onu da temizle
    #    (AIza ile başlayıp 35 karakter devam eder)
    return re.sub(r"AIza[0-9A-Za-z_\-]{35}", "***", safe)


# ── Gemini (Görüntü Analizi) Ayarları ───────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"

# Gemini'nin "düşünme" (thinking) bütçesi. 0 = kapalı.
#
# Gemini 2.5 modelleri cevap vermeden önce içlerinden akıl yürütür. Bu,
# çok adımlı problemlerde işe yarar; ama fotoğraf betimleme tek adımlık
# bir iş olduğu için burada sadece bekleme süresi ekliyor.
#
# Ölçüm (aynı fotoğraf, 4'er tur):
#   Düşünme açık  : ortalama 11.80 sn
#   Düşünme kapalı: ortalama  1.87 sn   → %84 daha hızlı
#
# Betimleme kalitesinde fark görülmedi: uzunluk, konum bilgisi ve
# uyarı cümleleri her iki durumda da aynı kaldı.
GEMINI_THINKING_BUDGET = 0

# Gemini'ye gönderilecek Türkçe prompt (adaptif)
VISION_PROMPT = (
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


# ── Ses (Google Cloud TTS - Chirp3 HD) Ayarları ─────────────────────────────

GOOGLE_TTS_VOICE = "tr-TR-Chirp3-HD-Achernar"

# Sıkıştırılmamış WAV kullanılıyor: ses kalitesi MP3'e göre belirgin daha iyi.
# Karşılığında dosya büyük olduğu için indirme süresi uzuyor (bilinçli tercih).
TTS_OUTPUT_FILE = "output.wav"


# ── Raspberry Pi Donanım Ayarları ───────────────────────────────────────────

# Buton bağlantısı:
#   Pin 11 (GPIO17, BCM) → butonun bir ayağı
#   Pin 6  (GND)         → butonun diğer ayağı
GPIO_BUTTON_PIN = 17

# Full HD çekim: Gemini'nin küçük detayları (tabela yazısı, basamak kenarı)
# ayırt edebilmesi için yüksek çözünürlük tercih edildi.
CAMERA_RESOLUTION = (1920, 1080)

# Kameranın otomatik pozlama/odak ayarlarını oturtması için beklenen süre.
# Fotoğrafın net çıkması için gerekli (bilinçli tercih).
CAMERA_WARMUP_SECONDS = 1.5


# ── Test Modu Ayarları ──────────────────────────────────────────────────────

# Raspberry Pi kamerası bulunamazsa (örneğin Windows'ta geliştirme yaparken)
# kamera yerine bu fotoğraf kullanılır.
TEST_IMAGE_PATH = "test.jpg"
