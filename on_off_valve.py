#!/usr/bin/env python3
"""Start the valve closed (180°); press Enter to toggle open (0°) and closed."""

import argparse
import signal

from run import interrupted, run


def valve_angles():
    is_on = False
    yield 180
    while True:
        print("ON / OPEN (0°)" if is_on else "OFF / CLOSED (180°)", flush=True)
        try:
            command = input("Enter to toggle, q to quit: ").strip().lower()
        except EOFError:
            return
        if command in ("q", "quit", "exit"):
            return
        if command:
            print("Press Enter to toggle, or q to quit.")
            continue
        is_on = not is_on
        yield 0 if is_on else 180


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="preview without GPIO access")
    args = parser.parse_args()
    print("GPIO23 / physical pin 16: start OFF (180°); Enter toggles ON (0°) / OFF (180°).", flush=True)
    if args.dry_run:
        return 0
    try:
        import lgpio
    except ImportError:
        print("Run on nixzero: sudo nix develop --command python3 on_off_valve.py")
        return 1
    signal.signal(signal.SIGTERM, interrupted)
    try:
        run(lgpio, valve_angles())
    except KeyboardInterrupt:
        print("Stopped; GPIO23 released.")
        return 130
    except (lgpio.error, OSError, RuntimeError) as error:
        print(f"GPIO error: {error}")
        return 1
    print("Stopped; GPIO23 released.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
