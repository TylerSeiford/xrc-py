import time
from models import Alliance, Gamepad
from rapid_react_67 import RR67State, RR67Controls, COMMANDS



FPS: float = 100
ALLIANCE: Alliance = Alliance.BLUE



if __name__ == '__main__':
    gamepad = Gamepad()

    while True:
        start = time.time()
        with (open('GAME_STATE.txt', 'rt', encoding='UTF+8') as game_file,
                open('GameElements.txt', 'rt', encoding='UTF+8') as element_file,
                open('myRobot.txt', 'rt', encoding='UTF+8') as robot_file):
            state = RR67State.read(game_file, element_file, robot_file, gamepad, ALLIANCE)
            if state is None:
                continue
            control_outputs = RR67Controls.from_gamepad_state(state.gamepad)
            for command in COMMANDS:
                control_outputs = command.execute(state, control_outputs)
            control_outputs.write()
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
