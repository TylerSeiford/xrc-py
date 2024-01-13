import time
import keyboard
from models import AutomationProvider, Gamepad, Logger
from charged_up_254 import CU254AutomationProvider


FPS: float = 240
AUTOMATION: AutomationProvider = CU254AutomationProvider()


if __name__ == '__main__':
    gamepad = Gamepad()

    Logger.log(
        'body global position,,,'
        'body global rotation,,,'
        'nearest global position,,,'
        'delta,,,,'
        'lift local position,,,,'
        'slide local position,,,,'
        'slide 2 local position,,,,'
        'intake 1 local position,,,,'
        'intake 2 local position,,,,'
        'intake 3 local position,,,,'
        'intake 4 local position,,,,'
        'intake average position,,,,'
        'intake rotated position,,,,'
        'lift rotated position,,,,'
        'slide rotated position,,,,'
        'slide 2 rotated position,,,,'
        'guess,,,,'
    )
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
