# timing.py - Adım Sürelerini Ölçme
# -----------------------------------------------
# Bu modülün tek işi: her adımın kaç saniye sürdüğünü ölçmek ve sonunda
# tablo halinde göstermek. Böylece gecikmenin hangi adımdan kaynaklandığı
# tahmin edilmek yerine ölçülerek görülür.
#
# Kullanımı:
#     timer = StepTimer()
#     with timer.measure("Kamera"):
#         ...ölçülecek işlem...
#     timer.print_report()

import time
from contextlib import contextmanager


class StepTimer:
    """Boru hattındaki adımların sürelerini sırayla kaydeder."""

    def __init__(self) -> None:
        # [(adım adı, süre saniye, gecikmeye dahil mi), ...] şeklinde tutulur
        self.steps: list[tuple[str, float, bool]] = []

    @contextmanager
    def measure(self, name: str, is_latency: bool = True):
        """
        Bir adımın süresini ölçer.

        'with' bloğuna girildiğinde saat başlar, çıkıldığında durur.
        İşlem hata verse bile süre kaydedilir (hatanın ne kadar sürdüğü de
        bilgidir) ve hata normal şekilde yukarı iletilir.

        Args:
            name: Tabloda görünecek adım adı
            is_latency: Bu adım "gecikme"ye dahil mi?
                Kullanıcı sesin BAŞLAMASINI bekler, bitmesini değil. Bu yüzden
                sesin çalma süresi bir bekleme değildir; konuşmanın kendi
                uzunluğudur ve gecikme sayılmaz (is_latency=False).
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            self.steps.append((name, time.perf_counter() - start, is_latency))

    @property
    def latency_total(self) -> float:
        """Kullanıcının beklediği süre: tetiklemeden ilk sese kadar."""
        return sum(d for _, d, is_latency in self.steps if is_latency)

    @property
    def total(self) -> float:
        """Tüm adımların toplam süresi (ses çalma dahil)."""
        return sum(duration for _, duration, _ in self.steps)

    def print_report(self) -> None:
        """
        Ölçüm sonuçlarını tablo halinde yazdırır.

        Gecikme adımları ile ses çalma süresi ayrı gösterilir: ikisini tek
        toplamda birleştirmek gecikmeyi olduğundan büyük gösterirdi.
        """
        if not self.steps:
            return

        latency = self.latency_total

        print()
        print("  ┌─ Süre Ölçümü " + "─" * 36)

        for name, duration, is_latency in self.steps:
            if is_latency:
                share = (duration / latency * 100) if latency else 0
                print(f"  │ {name:<24} {duration:>6.2f} sn   %{share:>4.1f}")

        print("  ├" + "─" * 49)
        print(f"  │ {'► SESE KADAR (gecikme)':<24} {latency:>6.2f} sn")
        print("  ├" + "─" * 49)

        for name, duration, is_latency in self.steps:
            if not is_latency:
                print(f"  │ {name:<24} {duration:>6.2f} sn  (gecikme değil)")

        print(f"  │ {'TOPLAM':<24} {self.total:>6.2f} sn")
        print("  └" + "─" * 49)
