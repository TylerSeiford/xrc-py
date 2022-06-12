# xrc-py

## Installation
You will need to download both `main.py` and `models.py` into the XRC simulation directory.  
You'll need Python 3.10, available from [python.org](https://www.python.org/downloads/), pygame (`pip install pygame`) and simple_pid (`pip install simple_pid`).
You may need to customize the FPS count at the start of `main.py` to match your setting, it defaults to 100.

## Controls
The default hood and precision controls have been replaced.  The hood control is automated using Eliot's lookup table with some tweaks.  The precision control has been replaced with a rotation PID controller.  The left bumper will target the nearest ball while pressed and right bumper will target the hub.  In two ball mode intake deployment is automated by deploying the correct intake when seeking a ball, and closing both when targeting the hub.  In three ball mode, both intakes stay down all the time.  To toggle between two and three ball mode, press the up and down dpad buttons.

## Feedback
To help prevent the robot from getting penalties for too many balls, the code will automatically start shooting 250 milliseconds before the penalty.

## Credit
The basis for most of this project is [Eliot's XRC-Automation](https://github.com/Coolgamertag/xRc-Automation).  The hood angles and a good amount of inspiration is from his project.
