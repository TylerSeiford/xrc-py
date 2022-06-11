import json
import math
import time
from models import Vector, GameElementState, RobotState, GameState, Controls, Gamepad



FPS: float = 100


def hood_control(robot_position: Vector, hood_rotation: Vector,
        control_input: Controls) -> Controls:
    HOOD_ANGLES = [
        180, 170, 162, 155, 147, 140, 132, 126, 120, 115,
        110, 105, 100, 95, 90, 85, 80, 75, 70, 66,
        62, 58, 54, 50, 47, 44, 41, 38, 36, 34,
        32
    ]
    distance = math.hypot(robot_position.x, robot_position.z)
    hood_index = int((distance - 1.3) * 10)
    hood_index = max(min(hood_index, 30), 0)
    target_hood_angle = HOOD_ANGLES[hood_index]
    hood_angle = hood_rotation.x
    if hood_angle > target_hood_angle:
        control_input.aim_up = False
        control_input.aim_down = True
    elif hood_angle < target_hood_angle:
        control_input.aim_up = True
        control_input.aim_down = False
    return control_input


if __name__ == '__main__':
    gamepad = Gamepad()

    while True:
        start = time.time()
        with (open('GAME_STATE.txt', 'rt', encoding='UTF+8') as game_file,
                open('GameElements.txt', 'rt', encoding='UTF+8') as element_file,
                open('myRobot.txt', 'rt', encoding='UTF+8') as robot_file):
            try:
                game_state = GameState.read(game_file)
                element_state = GameElementState.read(element_file)
                robot_state = RobotState.read(robot_file)
            except json.JSONDecodeError:
                continue # Error reading file, try again
            except ValueError:
                continue # Error reading file, try again
            controls = gamepad.read()
            controls = hood_control(robot_state.body.position, robot_state.hood.rotation, controls)
            controls.write()
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
