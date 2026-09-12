#!/usr/bin/env python3
"""Play a short servo choreography on GPIO23 / physical pin 16."""

import argparse
import math
import signal
import time

GPIO = 23
FREQUENCY = 50
PERIOD_US = 20_000


def choreography(pattern):
    """Return labelled pulse trains and the pause after each train."""
    if pattern == "demo":
        # Preserve the sequence used when movement was reported.
        return [(f"{width} us", [width] * 100, 1) for width in (1500, 1000, 2000)]

    widths = []

    def hold(width, seconds):
        widths.extend([width] * round(seconds * FREQUENCY))

    def glide(target, seconds):
        start = widths[-1]
        count = round(seconds * FREQUENCY)
        for index in range(1, count + 1):
            fraction = (1 - math.cos(math.pi * index / count)) / 2
            widths.append(round(start + (target - start) * fraction))

    hold(1500, 0.5)
    glide(1100, 0.7)
    hold(1100, 0.2)
    glide(1900, 1.2)
    hold(1900, 0.3)
    glide(1500, 0.6)
    for _ in range(2):
        glide(1350, 0.16)
        glide(1650, 0.16)
    glide(1500, 0.3)
    hold(1500, 0.3)
    glide(1000, 1.0)
    glide(2000, 1.4)
    glide(1500, 0.8)
    hold(1500, 0.5)
    return [("look left/right, double wiggle, slow sweep, return to centre", widths, 0)]


def play(lgpio, sequence):
    handle = lgpio.gpiochip_open(0)
    claimed = False
    try:
        chip = lgpio.gpio_get_chip_info(handle)
        if chip[3] != "pinctrl-bcm2835":
            raise RuntimeError(f"Unexpected GPIO controller: {chip[3]!r}")
        lgpio.gpio_claim_output(handle, GPIO, 0)
        claimed = True
        for label, widths, pause in sequence:
            pulses = []
            for width in widths:
                # A singleton GPIO group uses bit 0, regardless of its BCM number.
                pulses.extend((lgpio.pulse(1, 1, width),
                               lgpio.pulse(0, 1, PERIOD_US - width)))
            print(f"Playing: {label} ({len(widths) / FREQUENCY:.2f}s)", flush=True)
            lgpio.tx_wave(handle, GPIO, pulses)
            deadline = time.monotonic() + len(widths) / FREQUENCY + 1
            while lgpio.tx_busy(handle, GPIO, lgpio.TX_WAVE):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Wave exceeded its completion deadline")
                time.sleep(0.01)
            if pause:
                time.sleep(pause)
    finally:
        try:
            if claimed:
                # Free also cancels any outstanding wave on interruption.
                lgpio.gpio_free(handle, GPIO)
        finally:
            lgpio.gpiochip_close(handle)


def interrupted(*_):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", choices=("dance", "demo"), default="dance",
                        help="dance (default), or the original three-position demo")
    parser.add_argument("--dry-run", action="store_true", help="preview without GPIO access")
    args = parser.parse_args()
    sequence = choreography(args.pattern)
    duration = sum(len(widths) / FREQUENCY + pause for _, widths, pause in sequence)
    print(f"GPIO23 / physical pin 16: {args.pattern}, {duration:.2f}s, queued waves at 50 Hz.", flush=True)
    if args.dry_run:
        for label, widths, _ in sequence:
            print(f"{label}: {len(widths)} pulses, {min(widths)}–{max(widths)} us")
        return 0

    try:
        import lgpio
    except ImportError:
        print("Run on nixzero: sudo nix develop --command python3 servo_wave.py")
        return 1
    signal.signal(signal.SIGTERM, interrupted)
    try:
        play(lgpio, sequence)
    except KeyboardInterrupt:
        print("Interrupted; GPIO released.")
        return 130
    except (lgpio.error, OSError, RuntimeError) as error:
        print(f"Wave error: {error}")
        return 1
    print("Finished; GPIO23 released.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
