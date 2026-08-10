# Answers one question: did the user ask for a photo?
#
# Uses the GPIO button when gpiozero is available, and falls back to the
# Enter key otherwise.
#
# Wiring: pin 11 (GPIO 17, BCM) to one button leg, pin 6 (GND) to the other.
# Pressing the button ties GPIO 17 to ground, so the Pi's internal pull-up is
# enabled: the pin idles HIGH and reads LOW when pressed. No external
# resistor required.

from config import GPIO_BUTTON_PIN

# gpiozero is only meaningful on a Raspberry Pi. The except is broad on
# purpose: even when installed, it can fail off-Pi because no pin factory
# is available.
try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except Exception:
    GPIO_AVAILABLE = False

_button = None


def is_button_mode() -> bool:
    """True when the GPIO button is usable."""
    return GPIO_AVAILABLE


def _get_button() -> "Button":
    """Return the button, creating it on first call."""
    global _button

    if _button is None:
        _button = Button(GPIO_BUTTON_PIN, pull_up=True)

    return _button


def wait_for_trigger() -> bool:
    """Block until the user acts.

    Returns:
        True to take a photo, False to quit.
    """
    if GPIO_AVAILABLE:
        return _wait_for_button()

    return _wait_for_enter()


def _wait_for_button() -> bool:
    """Wait for a GPIO button press.

    In button mode the only way out is Ctrl+C, which arrives as
    KeyboardInterrupt and counts as a request to quit.
    """
    print("  📸 Fotoğraf çekmek için butona bas (çıkış için Ctrl+C)")
    try:
        _get_button().wait_for_press()
        return True
    except KeyboardInterrupt:
        return False


def _wait_for_enter() -> bool:
    """Wait for the Enter key, used when no button is present."""
    try:
        raw = input("  📸 Fotoğraf çekmek için Enter'a bas (veya q=çıkış): ").strip()
    except (KeyboardInterrupt, EOFError):
        return False

    return raw.lower() not in ("q", "quit", "exit", "çıkış")
