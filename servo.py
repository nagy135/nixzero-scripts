#!/usr/bin/env python3
"""Briefly position a hobby servo on nixzero (GPIO18 or GPIO23)."""

import argparse
import math
import signal
import sys
import time


HEADER_PINS = {18: 12, 23: 16}


def bounded_number(low, high):
    def parse(value):
        try:
            number = float(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("must be a number") from error
        if not math.isfinite(number) or not low <= number <= high:
            raise argparse.ArgumentTypeError(f"must be between {low} and {high}")
        return number
    return parse


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpio", type=int, choices=HEADER_PINS, default=18,
                        help="BCM GPIO number: 18 = physical pin 12 (default), 23 = physical pin 16")
    parser.add_argument("--backend", choices=("lgpio", "direct"), default="lgpio",
                        help="pulse generator: lgpio PWM (default), or direct GPIO switching")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--angle", type=bounded_number(0, 180),
                        help="nominal angle, 0–180 degrees; default: 90 (centre)")
    target.add_argument("--pulse-us", type=bounded_number(1000, 2000),
                        help="send a pulse width directly, between 1000 and 2000 µs")
    parser.add_argument("--duration", type=bounded_number(0.1, 10), default=1.0,
                        help="seconds to send pulses before releasing the servo (default: 1)")
    parser.add_argument("--check", action="store_true",
                        help="inspect the GPIO chip and line without claiming or driving them")
    parser.add_argument("--dry-run", action="store_true",
                        help="show the command without opening any GPIO device")
    return parser.parse_args()


def interrupted(_signum, _frame):
    raise KeyboardInterrupt


def direct_pulses(lgpio, handle, gpio, pulse_us, frequency, cycles):
    """Bench-test pulses using the direct writes that moved the servo."""
    for _ in range(cycles):
        start = time.perf_counter_ns()
        try:
            lgpio.gpio_write(handle, gpio, 1)
            high_start = time.perf_counter_ns()
            while time.perf_counter_ns() - high_start < pulse_us * 1000:
                pass
        finally:
            lgpio.gpio_write(handle, gpio, 0)
        remaining = 1 / frequency - (time.perf_counter_ns() - start) / 1e9
        if remaining > 0:
            time.sleep(remaining)


def release_servo(lgpio, handle, gpio=18):
    """Stop any remaining pulses, drive low, and release the line."""
    try:
        try:
            if lgpio.tx_busy(handle, gpio, lgpio.TX_PWM):
                try:
                    lgpio.tx_servo(handle, gpio, 0)
                except lgpio.error as error:
                    # lgpio 0.2.2 rejects stopping an already finished train.
                    # It can finish between tx_busy() and tx_servo().
                    if (str(error) != repr(lgpio.error_text(lgpio.BAD_PWM_MICROS))
                            or lgpio.tx_busy(handle, gpio, lgpio.TX_PWM)):
                        raise
        finally:
            lgpio.gpio_write(handle, gpio, 0)
    finally:
        lgpio.gpio_free(handle, gpio)


def main():
    args = arguments()
    gpio = args.gpio
    angle = 90 if args.angle is None else args.angle
    pulse = round(args.pulse_us if args.pulse_us is not None else 1000 + angle * 1000 / 180)
    frequency = 50
    cycles = math.ceil(args.duration * frequency)
    print(f"GPIO{gpio} / physical pin {HEADER_PINS[gpio]}: {pulse} µs at {frequency} Hz, {cycles} pulses.")
    print(f"Pulse backend: {args.backend}.")
    if args.dry_run:
        print("Dry run: no GPIO access.")
        return 0

    try:
        import lgpio
    except ImportError:
        print("Missing lgpio. On nixzero, run: sudo nix run . -- --angle 90", file=sys.stderr)
        return 1

    signal.signal(signal.SIGTERM, interrupted)
    try:
        handle = lgpio.gpiochip_open(0)
        try:
            chip = lgpio.gpio_get_chip_info(handle)
            if chip[3] != "pinctrl-bcm2835":
                raise RuntimeError(f"Expected nixzero's pinctrl-bcm2835 GPIO controller; found {chip[3]!r}.")
            line = lgpio.gpio_get_line_info(handle, gpio)
            if args.check:
                print(f"Controller: {chip[3]}; GPIO{gpio} name: {line[3]!r}; consumer: {line[4]!r}.")
                print("Check only: no GPIO was claimed or driven.")
                return 0

            lgpio.gpio_claim_output(handle, gpio, 0)
            try:
                if args.backend == "direct":
                    direct_pulses(lgpio, handle, gpio, pulse, frequency, cycles)
                else:
                    lgpio.tx_servo(handle, gpio, pulse, servo_frequency=frequency, pulse_cycles=cycles)
                    time.sleep(cycles / frequency + 0.05)
            finally:
                release_servo(lgpio, handle, gpio)
        finally:
            lgpio.gpiochip_close(handle)
    except KeyboardInterrupt:
        print("Interrupted; servo signal released.")
        return 130
    except (lgpio.error, OSError, RuntimeError) as error:
        print(f"GPIO error: {error}", file=sys.stderr)
        return 1

    print("Finished; signal released. The servo is no longer commanded to hold position.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
