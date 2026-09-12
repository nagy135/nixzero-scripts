#!/usr/bin/env python3
"""Briefly position a hobby servo on nixzero's GPIO18 (physical pin 12)."""

import argparse
import math
import signal
import sys
import time


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


def main():
    args = arguments()
    angle = 90 if args.angle is None else args.angle
    pulse = round(args.pulse_us if args.pulse_us is not None else 1000 + angle * 1000 / 180)
    frequency = 50
    cycles = math.ceil(args.duration * frequency)
    print(f"GPIO18 / physical pin 12: {pulse} µs at {frequency} Hz, {cycles} pulses.")
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
            line = lgpio.gpio_get_line_info(handle, 18)
            if args.check:
                print(f"Controller: {chip[3]}; GPIO18 name: {line[3]!r}; consumer: {line[4]!r}.")
                print("Check only: no GPIO was claimed or driven.")
                return 0

            lgpio.gpio_claim_output(handle, 18, 0)
            try:
                lgpio.tx_servo(handle, 18, pulse, servo_frequency=frequency, pulse_cycles=cycles)
                time.sleep(cycles / frequency + 0.05)
            finally:
                try:
                    lgpio.tx_servo(handle, 18, 0)
                    lgpio.gpio_write(handle, 18, 0)
                finally:
                    lgpio.gpio_free(handle, 18)
        finally:
            lgpio.gpiochip_close(handle)
    except KeyboardInterrupt:
        print("Interrupted; servo signal released.")
        return 130
    except (lgpio.error, OSError, RuntimeError) as error:
        print(f"GPIO error: {error}. Run as root on nixzero and check that GPIO18 is free.", file=sys.stderr)
        return 1

    print("Finished; signal released. The servo is no longer commanded to hold position.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
