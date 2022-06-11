# xrc-py
## Installation
You will need to download both `main.py` and `models.py` in the XRC simulation directory.  
You'll need python 3.10, available from [python.org/downloads/](https://www.python.org/downloads/), pygame (`pip install pygame`) and simple_pid (`pip install simple_pid`).
You may need to customize the FPS count on line 9 of `main.py` to match your setting, it defaults to 100.
## Controls
The default hood and precision controls have been replaced.  The hood control is automated using Eliot's lookup table.  The precision control has been replaced with a rotation PID controller.  The left bumper will target the nearest ball while pressed, automatically deploying the correct intake.  The right bumper will target the hub, automatically closing both intakes.
