#!/usr/bin/env python3
"""Play a short servo choreography on GPIO23 / physical pin 16."""

import argparse
import math
import signal
import time

GPIO = 23
FREQUENCY = 50
PERIOD_US = 20_000


def angle_to_pulse(angle):
    """Map nominal degrees to the established 1000–2000 us pulse range."""
    if not math.isfinite(angle) or not 0 <= angle <= 180:
        raise ValueError("angle must be between 0 and 180 degrees")
    return round(1000 + angle * 1000 / 180)


def angle_argument(value):
    try:
        angle = float(value)
        angle_to_pulse(angle)
        return angle
    except ValueError as error:
        raise argparse.ArgumentTypeError("angle must be a number from 0 to 180 degrees") from error


def duration_argument(value):
    try:
        seconds = float(value)
        if not math.isfinite(seconds) or not 0.1 <= seconds <= 10:
            raise ValueError
        return seconds
    except ValueError as error:
        raise argparse.ArgumentTypeError("duration must be between 0.1 and 10 seconds") from error


def angle_sequence(angles, duration=1):
    return [(f"{angle:g}°", [angle_to_pulse(angle)] * math.ceil(duration * FREQUENCY), 0)
            for angle in angles]


def choreography(pattern):
    """Return labelled pulse trains and the pause after each train."""
    if pattern == "demo":
        # Preserve the sequence used when movement was reported.
        return [(f"{angle}°", [angle_to_pulse(angle)] * 100, 1) for angle in (90, 0, 180)]

    positions = []

    def hold(angle, seconds):
        positions.extend([angle] * round(seconds * FREQUENCY))

    def glide(target, seconds):
        start = positions[-1]
        count = round(seconds * FREQUENCY)
        for index in range(1, count + 1):
            fraction = (1 - math.cos(math.pi * index / count)) / 2
            positions.append(start + (target - start) * fraction)

    # Positions are degrees; times are seconds.
    hold(90, 0.5)
    glide(18, 0.7)
    hold(18, 0.2)
    glide(162, 1.2)
    hold(162, 0.3)
    glide(90, 0.6)
    for _ in range(2):
        glide(63, 0.16)
        glide(117, 0.16)
    glide(90, 0.3)
    hold(90, 0.3)
    glide(0, 1.0)
    glide(180, 1.4)
    glide(90, 0.8)
    hold(90, 0.5)
    widths = [angle_to_pulse(angle) for angle in positions]
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
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--pattern", choices=("dance", "demo"), default="dance",
                        help="dance (default), or the original three-position demo")
    target.add_argument("--angles", type=angle_argument, nargs="+", metavar="DEGREES",
                        help="visit these positions in order, each from 0 to 180 degrees")
    parser.add_argument("--duration", type=duration_argument, default=1,
                        help="seconds at each custom angle, 0.1–10 (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="preview without GPIO access")
    args = parser.parse_args()
    sequence = (angle_sequence(args.angles, args.duration) if args.angles is not None
                else choreography(args.pattern))
    duration = sum(len(widths) / FREQUENCY + pause for _, widths, pause in sequence)
    name = "custom angles" if args.angles is not None else args.pattern
    print(f"GPIO23 / physical pin 16: {name}, {duration:.2f}s, queued waves at 50 Hz.", flush=True)
    if args.dry_run:
        for label, widths, _ in sequence:
            print(f"{label}: {len(widths) / FREQUENCY:.2f}s")
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
