# xrc-py

## Installation
You will need to download both `main.py` and `models.py` into the XRC simulation directory.  
You'll need Python 3.10, available from [python.org](https://www.python.org/downloads/), pygame (`pip install pygame`) and simple_pid (`pip install simple_pid`).
You may need to customize the FPS count at the start of `main.py` to match your setting, it defaults to 100.  Note, the script currently only works when on the blue alliance.

## Controls and Automation
The manual hood control is automated using Eliot's lookup table with some tweaks.  The precision control has been replaced with a rotation PID controller.  The left bumper will target the nearest ball while pressed and right bumper will target the hub.  In three ball mode (the default), both intakes stay down all the time.  In two ball mode intake deployment is automated by deploying the correct intake when seeking a ball, and closing both when targeting the hub.  To toggle between two and three ball mode, press the up and down dpad buttons.  The climber will auto-deploy when in the hangar in the endgame.

## Feedback
To help prevent the robot from getting penalties for too many balls, the code will automatically start shooting before the penalty occurs.

## Credit
The inspiration for most of this project is [Eliot's XRC-Automation](https://github.com/Coolgamertag/xRc-Automation).  The hood angles are directly from his project.
