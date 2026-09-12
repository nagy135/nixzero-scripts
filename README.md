# nixzero-scripts

`run.py` alternates a positional servo between **0° and 90° every two seconds**,
repeating until Ctrl-C. It uses queued lgpio waveforms on the Raspberry Pi Zero
2 W, at 50 Hz. Angles are nominal; actual travel depends on the servo.

## Wiring

Current setup, using physical header numbers:

| Wire | Pin |
| --- | --- |
| Red | **2 — 5 V** |
| Black/brown | **6 — GND** |
| Yellow/orange | **16 — GPIO23** |

Disconnect power before changing wiring. Use a power supply appropriate for the
servo's current requirements; an external servo supply must share ground with
the Pi. GPIO23 is the signal connection, not a power supply.

## Run on nixzero

```sh
cd ~/nixzero-scripts
git pull --ff-only
sudo nix develop --command python3 run.py
```

Ctrl-C cancels the wave and releases GPIO23. It does not disconnect servo power.
The default Nix package also runs this script: `sudo nix run .`.

To change the positions, edit `ANGLES = (0, 90)` in `run.py`; values are degrees.
Each two-second position uses a finite waveform, with a timeout if it fails to
finish. Software timing can jitter under Linux load.

## Check without moving

```sh
python3 run.py --dry-run
python3 -m unittest discover -v
```

Tests use mocked GPIO and do not establish physical movement. Commit and push
from the Mac checkout; pull from GitHub on nixzero.
