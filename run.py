#!/usr/bin/env python3
"""Alternate between 0° and 90° every two seconds on GPIO23 / physical pin 16."""

import argparse
import itertools
import math
import signal
import time

GPIO = 23
ANGLES = (0, 90)
HOLD_SECONDS = 2
FREQUENCY = 50
PERIOD_US = 20_000


def angle_to_pulse(angle):
    if not math.isfinite(angle) or not 0 <= angle <= 180:
        raise ValueError("angle must be between 0 and 180 degrees")
    return round(1000 + angle * 1000 / 180)


def run(lgpio):
    waves = []
    for angle in ANGLES:
        width = angle_to_pulse(angle)
        pulses = []
        for _ in range(HOLD_SECONDS * FREQUENCY):
            # A singleton GPIO group uses bit 0, regardless of its BCM number.
            pulses.extend((lgpio.pulse(1, 1, width),
                           lgpio.pulse(0, 1, PERIOD_US - width)))
        waves.append((angle, pulses))

    handle = lgpio.gpiochip_open(0)
    claimed = False
    try:
        chip = lgpio.gpio_get_chip_info(handle)
        if chip[3] != "pinctrl-bcm2835":
            raise RuntimeError(f"Unexpected GPIO controller: {chip[3]!r}")
        lgpio.gpio_claim_output(handle, GPIO, 0)
        claimed = True
        for angle, pulses in itertools.cycle(waves):
            print(f"{angle}°", flush=True)
            lgpio.tx_wave(handle, GPIO, pulses)
            deadline = time.monotonic() + HOLD_SECONDS + 1
            while lgpio.tx_busy(handle, GPIO, lgpio.TX_WAVE):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Wave exceeded its completion deadline")
                time.sleep(0.01)
    finally:
        try:
            if claimed:
                lgpio.gpio_free(handle, GPIO)  # Cancels any outstanding wave.
        finally:
            lgpio.gpiochip_close(handle)


def interrupted(*_):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="preview without GPIO access")
    args = parser.parse_args()
    print("GPIO23 / physical pin 16: 0° ↔ 90°, two seconds each. Ctrl-C to stop.", flush=True)
    if args.dry_run:
        return 0
    try:
        import lgpio
    except ImportError:
        print("Run on nixzero: sudo nix develop --command python3 run.py")
        return 1
    signal.signal(signal.SIGTERM, interrupted)
    try:
        run(lgpio)
    except KeyboardInterrupt:
        print("Stopped; GPIO23 released.")
        return 130
    except (lgpio.error, OSError, RuntimeError) as error:
        print(f"GPIO error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
