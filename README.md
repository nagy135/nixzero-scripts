# nixzero-scripts

One Python script for briefly positioning a standard PWM hobby servo from the
Raspberry Pi Zero 2 W. It uses GPIO18, which is **physical header pin 12**.
Alternatively, select GPIO23 (**physical pin 16**) with `--gpio 23`.

## Wiring

Disconnect power before wiring. For a servo using the usual red/yellow/brown
colour convention:

| Servo wire | Connect to |
| --- | --- |
| Yellow — signal | Pi physical **pin 12**, BCM **GPIO18** |
| Brown — ground | Pi physical **pin 6 (GND)** **and** external servo supply negative |
| Red — power | External servo supply positive, at the servo's rated voltage |

The servo's voltage/current rating has not yet been identified. If it is a
5 V servo, use a regulated 5 V supply rated for its stall current. Keep the Pi
powered through its own USB power connector. Do not connect the external supply
positive to the Pi header, or connect the red wire to a signal GPIO or 3.3 V pin.
The shared ground connection is required for the signal to work.

Header numbering, viewed from the component side and starting at the marked
pin-1 end (pin 1 has a square pad):

```text
 1    2
 3    4
 5    6  ← ground / brown, also external supply negative
 7    8
 9   10
11   12  ← GPIO18 / yellow
...  ...
39   40
```

Confirm the connector labels or servo documentation before connecting power;
wire colours alone do not establish its voltage rating.

## Run on nixzero

Inside this repository on the Zero:

```sh
cd ~/nixzero-scripts

# Read-only GPIO check; does not move anything.
sudo nix run . -- --check

# Centre for one second, then release the signal.
sudo nix run . -- --angle 90

# Another nominal position, also held for only one second.
sudo nix run . -- --angle 45

# Or specify pulse width directly.
sudo nix run . -- --pulse-us 1500 --duration 2
```

To test a different signal pin, disconnect power and move only the yellow wire
from physical pin 12 to **physical pin 16 (GPIO23)**. Then power on and run:

```sh
sudo nix develop --command python3 servo.py --gpio 23 --check
sudo nix develop --command python3 servo.py --gpio 23 --angle 45 --duration 2
```

`--gpio` uses BCM numbering, not physical header numbering. The script supports
GPIO18 and GPIO23 and defaults to GPIO18. Both work with lgpio's software-timed
pulses; GPIO23 does not need a hardware PWM function.

The servo moved during the direct GPIO switching diagnostic on GPIO23. To use
that pulse generator, bypassing lgpio's PWM engine:

```sh
sudo nix develop --command python3 servo.py --gpio 23 --backend direct --angle 45 --duration 2
```

The direct backend uses a short busy-wait for each high pulse and sleeps between
pulses. It is still software-timed and intended for brief bench tests. Both
backends stop driving high and release the GPIO on completion or interruption.

The Mac working repository is `~/Code/nixzero-scripts`; an initial Git snapshot
is also installed at `~/nixzero-scripts` on the Zero. No hosted Git remote is
configured yet, so the two copies do not synchronize automatically.

Nix supplies Python and lgpio; no pip install or system rebuild is required.
The lock file uses the same Nixpkgs revision as the nixzero host. Its configured
nixpi build worker can build the package. The GPIO device is root-only, hence
`sudo`. For direct Python use, open a root shell, enter `nix develop`, then run
`python3 servo.py --angle 90`.

On the Mac, preview the pulse settings without lgpio or any GPIO access:

```sh
python3 servo.py --angle 45 --dry-run
```

Angles are nominal: 0–180 maps to 1000–2000 µs at 50 Hz. Actual travel depends on
the servo's calibration. Start at centre with no load attached. A continuous
rotation servo interprets pulse width as speed/direction, not an angle.

This is a short bench-test script. lgpio uses software-timed pulses, which can
jitter under Linux load; use a hardware PWM controller for sustained holding or
precision motion. The script sends only a bounded number of pulses (maximum
10 seconds), then drives the signal low and releases the GPIO. It also cleans
up on Ctrl-C and SIGTERM. Releasing the signal does not guarantee that an
unknown servo physically stops or becomes unpowered.

References: [Raspberry Pi GPIO header](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio),
[GPIO Zero servo wiring](https://gpiozero.readthedocs.io/en/stable/api_output.html#servo),
[lgpio Python API source](https://github.com/joan2937/lg/blob/v0.2.2/PY_LGPIO/lgpio_extra.py).
