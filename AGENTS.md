# Working on nixzero-scripts

## Scope and environment

- This repository contains Python hardware experiments for `nixzero`, a
  Raspberry Pi Zero 2 W running NixOS (`aarch64-linux`). It does not contain the
  host's NixOS configuration.
- The Mac checkout is `~/Code/nixzero-scripts`; the Pi checkout is
  `~/nixzero-scripts`. Both use `nagy135/nixzero-scripts` on GitHub. Local edits
  do not automatically reach the Pi; verify the remote checkout before running
  changed code there.
- Read `README.md` for wiring, usage, and the history of observed movement.
  Keep it consistent with CLI or hardware behavior changes.

## Repository map

- `servo.py`: briefly commands one position on BCM GPIO18 (physical pin 12)
  or GPIO23 (physical pin 16), defaulting to GPIO18. Supports lgpio PWM and a
  direct software pulse diagnostic, plus `--check` and `--dry-run`.
- `servo_wave.py`: queued lgpio waveforms, fixed to GPIO23 / physical pin 16.
  The default `dance` is a 4.5-second sequence with glides to 18°, 54°, 108°,
  and 144°, returning to centre between glides. `demo` preserves the earlier
  reported movement sequence; `--angles` accepts custom positions.
- `test_servo.py`, `test_servo_wave.py`: standard-library `unittest` tests
  using mocked GPIO and timing; they run without hardware or lgpio installed.
- `flake.nix`: supplies Python with lgpio. The default package runs `servo.py`;
  use the development shell to run `servo_wave.py`. Outputs exist only for
  `aarch64-linux`, so do not expect native Mac `nix run` / `nix develop` support.
- `flake.lock`: pins Nixpkgs; README records that this matches the nixzero
  host revision. Avoid incidental lock updates. The host's configured nixpi
  build worker can build the package.

## Development and verification

Run these from the repository root on the Mac or another machine with Python 3:

```sh
python3 -m unittest discover -v
python3 servo.py --angle 45 --dry-run
python3 servo_wave.py --dry-run
python3 servo_wave.py --angles 90 30 150 90 --duration 0.5 --dry-run
```

Dry runs return before importing lgpio or accessing GPIO. Preserve that property.
Use the existing mocked tests for changes to pulse generation, validation, and
cleanup. Passing tests or previews does not establish physical servo movement.

On nixzero, the following inspects GPIO without claiming or driving it:

```sh
cd ~/nixzero-scripts
sudo nix run . -- --check
```

For an intended hardware movement test, the entry points are:

```sh
sudo nix run . -- --angle 90
sudo nix develop --command python3 servo_wave.py
```

These two commands use different signal pins (GPIO18 and GPIO23 respectively).
Running either script without `--dry-run` or the supported `--check` option
actuates hardware. Do not use an ordinary invocation as a generic smoke test.
GPIO access is root-only on the target; Nix supplies dependencies without pip
installation or a NixOS rebuild.

## Hardware and implementation constraints

- GPIO numbers are BCM numbers, not header positions. Both scripts open chip 0
  and require the controller label `pinctrl-bcm2835`; preserve this target check.
- The established range is 1000–2000 µs at 50 Hz (20,000 µs frames), mapping
  nominal 0–180° with 90° at 1500 µs. Actual travel and servo type are not
  established. Keep finite-number validation and pulse limits intact.
- `servo.py` limits duration to 0.1–10 seconds and rounds up to whole pulses.
  In `servo_wave.py`, `--duration` applies only to custom angles and limits
  each position to 0.1–10 seconds; it is not a total sequence duration limit.
  Keep experiments finite and brief.
- Preserve cleanup on normal completion, errors, Ctrl-C, and SIGTERM, including
  closing the chip. `servo.py` stops active PWM, drives low, and frees the line.
  Its lgpio 0.2.2 `BAD_PWM_MICROS` handling covers a train finishing between the
  busy check and stop call; do not suppress unrelated errors.
- Queued waves use bit **0** and mask **1** for the singleton GPIO group,
  regardless of the BCM pin number. Do not replace these with `1 << GPIO`.
  `gpio_free` cancels outstanding waves; preserve the completion deadline and
  cleanup in `finally` blocks.
- Direct pulses busy-wait during the high portion and sleep between pulses.
  Software timing can jitter under Linux load. README reports that direct
  switching did not reliably reproduce movement, while queued waves had a
  movement report. The current dance still needs physical observation; do not
  describe it as hardware-verified based on unit tests.
- Disconnect power before wiring. The servo needs an appropriately rated
  external supply and a common ground with the Pi; its voltage/current rating
  remains unknown. Do not connect supply positive to the Pi header or power the
  servo from a signal GPIO / 3.3 V pin. See README for the wiring table.
- Releasing the GPIO signal does not remove servo power or guarantee a physical
  stop. Keep that distinction in user-facing descriptions.
