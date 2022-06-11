import json
import math
import time
from simple_pid import PID
from models import Element, GameElementState, IntakeSide, RobotState, GameState, Controls, GamepadState, Gamepad



FPS: float = 100



def nearest_ball(robot: RobotState, balls: list[Element]) -> tuple[float, IntakeSide]:
    '''Find the angle to the nearest ball'''
    nearest_distance = float('inf')
    nearest_vector = None
    for ball in balls:
        difference = robot.body.global_position - ball.global_position
        distance = math.hypot(difference.x, difference.y, difference.z)
        if distance < 0.375:
            pass # Ball is in robot
        elif difference.y < -0.5:
            pass # Ball is still too high
        elif distance < nearest_distance:
            nearest_distance = distance
            nearest_vector = difference
    angle = math.degrees(math.atan2(nearest_vector.x, nearest_vector.z))
    angle = angle - robot.body.global_rotation.y
    if angle < -180:
        angle += 360
    elif angle > 180:
        angle -= 360

    # Wrap angle for dual intakes
    if angle > 90:
        angle -= 180
        intake = IntakeSide.LEFT
    elif angle < -90:
        angle += 180
        intake = IntakeSide.LEFT
    else:
        intake = IntakeSide.RIGHT
    return angle, intake


turn_pid = PID(-0.022, -0.000, -0.002, setpoint=0, output_limits=(-1, 1))
def control(robot: RobotState, game: GameElementState, gamepad_input: GamepadState) -> Controls:
    '''Semi-automated control'''
    # Find general info
    distance_to_hub = math.hypot(robot.body.global_position.x,
            robot.body.global_position.z)
    angle_from_hub = math.degrees(math.atan2(robot.body.global_position.x,
            robot.body.global_position.z))
    angle_to_hub = angle_from_hub - robot.body.global_rotation.y + 90
    if angle_to_hub < -180:
        angle_to_hub += 360
    elif angle_to_hub > 180:
        angle_to_hub -= 360
    angle_to_nearest_ball, nearest_intake = nearest_ball(robot, game.blue_cargo)

    # Automate hood angle control (based on Eliot's code)
    HOOD_ANGLES = [
        180, 170, 162, 155, 147,
        140, 132, 126, 120, 115,
        110, 105, 100, 95, 90,
        85, 80, 75, 70, 66,
        62, 58, 54, 50, 47,
        44, 41, 38, 36, 34,
        32
    ]
    hood_index = int((distance_to_hub - 1.3) * 10)
    hood_index = min(max(hood_index, 0), 30)
    target_hood_angle = HOOD_ANGLES[hood_index]
    hood_angle = robot.hood.local_rotation.x
    if hood_angle >= 270:
        hood_angle = (hood_angle - 450) * -1
    elif hood_angle <= 90:
        hood_angle = (hood_angle - 90) * -1
    if hood_angle > target_hood_angle:
        aim_up = False
        aim_down = True
    elif hood_angle < target_hood_angle:
        aim_up = True
        aim_down = False
    else:
        aim_up = False
        aim_down = False

    # Automate robot angle control and intake control
    rotation = gamepad_input.right_x
    toggle_left_intake = gamepad_input.x
    toggle_right_intake = gamepad_input.b
    if gamepad_input.bumper_right:
        # Turn to hub with both intakes up
        rotation = turn_pid(angle_to_hub)
        toggle_left_intake = not robot.intake_up(IntakeSide.LEFT)
        toggle_right_intake = not robot.intake_up(IntakeSide.RIGHT)
    elif gamepad_input.bumper_left:
        # Turn to ball with nearest intake down, other intake up
        rotation = turn_pid(angle_to_nearest_ball)
        toggle_left_intake = robot.intake_up(IntakeSide.LEFT) == (
                IntakeSide.LEFT == nearest_intake)
        toggle_right_intake = robot.intake_up(IntakeSide.RIGHT) == (
                IntakeSide.RIGHT == nearest_intake)

    return Controls(
        gamepad_input.a, toggle_right_intake, toggle_left_intake, gamepad_input.y,
        aim_down, aim_up,
        gamepad_input.dpad_left, gamepad_input.dpad_right,
        False, False, False, False,
        gamepad_input.right_y, rotation,
        gamepad_input.left_y, gamepad_input.left_x,
        gamepad_input.trigger_left, gamepad_input.trigger_right
    )


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

            # For default control, use: gamepad.read().default().write()
            controls = control(robot_state, element_state, gamepad.read())
            controls.write()
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
