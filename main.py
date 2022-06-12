import json
import math
import time
from simple_pid import PID
from models import Element, GameElementState, IntakeSide, RobotState, GameState, Controls, GamepadState, Gamepad, Command



FPS: float = 100



class MainCommand(Command):
    '''Automated control of rotation and intakes'''
    def __init__(self):
        self.__turn_pid = PID(-0.022, -0.000, -0.002, setpoint=0, output_limits=(-1, 1))

    @staticmethod
    def __ball_search(robot: RobotState, balls: list[Element]
            ) -> tuple[float, float, IntakeSide, int]:
        '''Find the angle & distance to nearest ball, nearest intake, and # of balls in robot'''
        nearest_distance = float('inf')
        nearest_vector = None
        balls_in_bot = 0
        for ball in balls:
            difference = robot.body.global_position - ball.global_position
            distance = math.hypot(difference.x, difference.y, difference.z)
            if distance < 0.375:
                # Ball is in robot
                balls_in_bot += 1
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
        return angle, nearest_distance, intake, balls_in_bot

    def execute(self,
            robot: RobotState, game: GameElementState, gamepad_input: GamepadState,
            controls: Controls) -> Controls:
        '''Execute'''
        # Gather data
        angle_from_hub = math.degrees(math.atan2(robot.body.global_position.x,
                robot.body.global_position.z))
        angle_to_hub = angle_from_hub - robot.body.global_rotation.y + 90
        if angle_to_hub < -180:
            angle_to_hub += 360
        elif angle_to_hub > 180:
            angle_to_hub -= 360
        (angle_to_nearest_ball, distance_to_nearest_ball,
            nearest_intake, balls_in_robot) = MainCommand.__ball_search(robot, game.blue_cargo)

        # Determine controls
        rotation = gamepad_input.right_x
        toggle_left_intake = gamepad_input.x
        toggle_right_intake = gamepad_input.b
        if gamepad_input.bumper_right:
            # Turn to hub with both intakes up
            rotation = self.__turn_pid(angle_to_hub)
            toggle_left_intake = not robot.intake_up(IntakeSide.LEFT)
            toggle_right_intake = not robot.intake_up(IntakeSide.RIGHT)
        elif gamepad_input.bumper_left:
            # Turn to ball, put nearby intake down and put far intake up
            rotation = self.__turn_pid(angle_to_nearest_ball)
            toggle_left_intake = robot.intake_up(IntakeSide.LEFT) == (
                    IntakeSide.LEFT == nearest_intake)
            toggle_right_intake = robot.intake_up(IntakeSide.RIGHT) == (
                    IntakeSide.RIGHT == nearest_intake)

        # Set controls
        controls.rotate = rotation
        controls.toggle_left_intake = toggle_left_intake
        controls.toggle_right_intake = toggle_right_intake
        return controls


class HoodCommand(Command):
    '''Automated control of the hood based on Eliot's angles'''
    def __init__(self):
        self.__hood_pid = PID(0.100, 0.001, 0.000, setpoint=0, output_limits=(-4, 4))

    def execute(self,
            robot: RobotState, game: GameElementState, gamepad_input: GamepadState,
            controls: Controls) -> Controls:
        '''Execute'''
        HOOD_ANGLES = [
            180, 170, 162, 155, 147,
            140, 132, 126, 120, 115,
            110, 105, 100, 95, 90,
            85, 80, 75, 70, 66,
            62, 58, 54, 50, 47,
            44, 41, 38, 36, 34,
            32
        ]
        distance_to_hub = math.hypot(robot.body.global_position.x,
            robot.body.global_position.z)
        hood_index = int((distance_to_hub - 1.3) * 10)
        hood_index = min(max(hood_index, 0), 30)
        target_hood_angle = HOOD_ANGLES[hood_index]
        hood_angle = robot.hood.local_rotation.x
        if hood_angle >= 270:
            hood_angle = (hood_angle - 450) * -1
        elif hood_angle <= 90:
            hood_angle = (hood_angle - 90) * -1
        # Use PID control for the hood angle
        angle_difference = target_hood_angle - hood_angle
        angle_output = self.__hood_pid(angle_difference)

        controls.aim_up = angle_output < 0
        controls.aim_down = angle_output > 0
        controls.precision_left = True
        controls.precision_right = True
        controls.precision = abs(angle_output)
        return controls



if __name__ == '__main__':
    gamepad = Gamepad()
    main_command = MainCommand()
    hood_command = HoodCommand()

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

            gamepad_state = gamepad.read()
            control_outputs = gamepad_state.default()
            control_outputs = main_command.execute(
                    robot_state, element_state, gamepad_state, control_outputs)
            control_outputs = hood_command.execute(
                    robot_state, element_state, gamepad_state, control_outputs)
            control_outputs.write()
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
