import time
from models import Alliance, AutomationProvider, Gamepad
from rapid_react_67 import RR67AutomationProvider



FPS: float = 100
ALLIANCE: Alliance = Alliance.BLUE
AUTOMATION: AutomationProvider = RR67AutomationProvider()



if __name__ == '__main__':
    gamepad = Gamepad()

    while True:
        start = time.time()
        with (open('GAME_STATE.txt', 'rt', encoding='UTF+8') as game_file,
                open('GameElements.txt', 'rt', encoding='UTF+8') as element_file,
                open('myRobot.txt', 'rt', encoding='UTF+8') as robot_file):
            AUTOMATION(game_file, element_file, robot_file, gamepad, ALLIANCE)
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
