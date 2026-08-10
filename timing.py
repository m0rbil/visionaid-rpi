# Measures how long each pipeline step takes, so the delay is observed
# rather than guessed at.
#
#     timer = StepTimer()
#     with timer.measure("Camera"):
#         ...
#     timer.print_report()

import time
from contextlib import contextmanager


class StepTimer:
    """Records the duration of each pipeline step in order."""

    def __init__(self) -> None:
        self.steps: list[tuple[str, float, bool]] = []

    @contextmanager
    def measure(self, name: str, is_latency: bool = True):
        """Time the enclosed block.

        The duration is recorded even when the block raises, and the error
        propagates normally.

        Args:
            name: label shown in the report.
            is_latency: whether this step counts towards perceived latency.
                The user waits for speech to START, not to finish, so
                playback duration is the length of the sentence rather than
                a delay and is excluded.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            self.steps.append((name, time.perf_counter() - start, is_latency))

    @property
    def latency_total(self) -> float:
        """Time from trigger to first audio."""
        return sum(d for _, d, is_latency in self.steps if is_latency)

    @property
    def total(self) -> float:
        """Total time including playback."""
        return sum(duration for _, duration, _ in self.steps)

    def print_report(self) -> None:
        """Print the results, keeping latency and playback separate.

        Combining them into a single total would overstate the delay.
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
