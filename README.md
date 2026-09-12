# nixzero-scripts

`run.py` asks for an angle from **0° to 180°**, moves the servo there, and asks
for the next angle. It uses queued lgpio waveforms on the Raspberry Pi Zero
2 W, at 50 Hz. Angles are nominal; actual travel depends on the servo.

## On/off valve

```sh
cd ~/nixzero-scripts
git pull --ff-only
sudo nix develop --command python3 on_off_valve.py
```

The valve is commanded **OFF / closed at 180° immediately on startup**. Each
Enter toggles between **ON / open at 0°** and **OFF / closed at 180°**. Each
movement sends two seconds of pulses, then prompts again. Type `q` or press
Ctrl-C to quit. Quitting releases the signal without commanding another position;
it does not automatically close the valve or disconnect power.

`python3 on_off_valve.py --dry-run` previews the behavior without GPIO access.

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

At the prompt, type an angle such as `90`, `30`, or `135.5`, then press Enter.
Each request sends two seconds of pulses, then waits for your next input without
continuing to command the servo to hold. Invalid input is rejected without moving.

Enter `q` to quit. Ctrl-C cancels the wave and releases GPIO23. Quitting does not
disconnect servo power.
The default Nix package also runs this script: `sudo nix run .`.

Each two-second position uses a finite waveform, with a timeout if it fails to
finish. Software timing can jitter under Linux load.

## Check without moving

```sh
python3 run.py --dry-run
python3 -m unittest discover -v
```

Tests use mocked GPIO and do not establish physical movement. Commit and push
from the Mac checkout; pull from GitHub on nixzero.
