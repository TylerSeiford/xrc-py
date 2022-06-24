import time
import keyboard
from models import Alliance, AutomationProvider, Gamepad, Logger
from rapid_react_67 import RR67AutomationProvider



FPS: float = 100
AUTOMATION: AutomationProvider = RR67AutomationProvider()



if __name__ == '__main__':
    gamepad = Gamepad()

    Logger.log('Timestamp,Current,Error,Output,P,I,D')
    while True:
        start = time.time()
        with (open('GAME_STATE.txt', 'rt', encoding='UTF+8') as game_file,
                open('GameElements.txt', 'rt', encoding='UTF+8') as element_file,
                open('myRobot.txt', 'rt', encoding='UTF+8') as robot_file):
            AUTOMATION(game_file, element_file, robot_file, gamepad)
        if keyboard.is_pressed('esc'):
            break
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
    Logger.save('log.csv')
