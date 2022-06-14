# xrc-py

## Installation
You will need to download both `main.py` and `models.py` into the XRC simulation directory.  
You'll need Python 3.10, available from [python.org](https://www.python.org/downloads/), pygame (`pip install pygame`) and simple_pid (`pip install simple_pid`).
You may need to customize the FPS count at the start of `main.py` to match your setting, it defaults to 100.  Note, the script currently only works when on the blue alliance.

## Controls and Automation
The manual hood control is automated using a lookup table with some tweaks.  The precision control has been replaced with a rotation PID controller.  The left bumper will target the nearest cargo while pressed and right bumper will target the hub.  In three cargo mode (the default), both intakes stay down all the time.  In two cargo mode intake deployment is automated by deploying the correct intake when seeking a cargo, and closing both when targeting the hub.  To toggle between two and three cargo mode, press the up and down dpad buttons.  To enable all cargo mode, press up on the right joystick.  The climber will auto-deploy when in the hangar in the endgame, and then once above the mid rung it will finish the climb to traversal.

## Feedback
To help prevent the robot from getting penalties for too many cargo, the code will automatically start shooting before the penalty occurs unless in all cargo mode.

## Credit
The inspiration for most of this project is [Eliot's XRC-Automation](https://github.com/Coolgamertag/xRc-Automation).
