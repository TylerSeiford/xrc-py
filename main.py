import time
from enum import Enum
from simple_pid import PID
from models import IntakeSide, GamePhase, Alliance, Controls, Gamepad, State, Command



FPS: float = 100
ALLIANCE: Alliance = Alliance.RED
THREE_CARGO_TIME_LIMIT: float = 1.625


class MainCommand(Command):
    '''Automated control of rotation and intakes'''
    class Mode(Enum):
        '''Represents the mode'''
        TWO_CARGO = 2
        THREE_CARGO = 3
        ALL_CARGO = 4

    def __init__(self):
        super().__init__()
        self.__pid = PID(-0.022, -0.000, -0.002, setpoint=0, output_limits=(-1, 1))
        self.__mode = MainCommand.Mode.THREE_CARGO
        self.__three_cargo_start = None

    def execute(self, state: State, controls: Controls) -> Controls:
        '''Execute'''
        # Gather data
        angle_to_hub = state.angle_to_hub()
        angle_to_nearest_cargo, _, nearest_intake = state.nearest_cargo_info()
        cargo_in_robot = len(state.cargo_in_robot())

        # Update cargo data
        if self.__three_cargo_start is None:
            if cargo_in_robot >= 3:
                self.__three_cargo_start = time.time()
        else:
            if cargo_in_robot < 3:
                self.__three_cargo_start = None
            else:
                time_left = THREE_CARGO_TIME_LIMIT - (time.time() - self.__three_cargo_start)
                if time_left < 0.25 and self.__mode != MainCommand.Mode.ALL_CARGO:
                    # Shoot cargo to avoid penalty
                    controls.shoot = True

        # Update mode
        if state.gamepad.right_y < -0.875 and self.__mode != MainCommand.Mode.ALL_CARGO:
            self.__mode = MainCommand.Mode.ALL_CARGO
            print(f"Switching to {self.__mode.name}")
        if state.gamepad.dpad_up and self.__mode != MainCommand.Mode.THREE_CARGO:
            self.__mode = MainCommand.Mode.THREE_CARGO
            print(f"Switching to {self.__mode.name}")
        elif state.gamepad.dpad_down and self.__mode != MainCommand.Mode.TWO_CARGO:
            self.__mode = MainCommand.Mode.TWO_CARGO
            print(f"Switching to {self.__mode.name}")

        # Determine controls
        rotation = state.gamepad.right_x
        toggle_left_intake = state.gamepad.x
        toggle_right_intake = state.gamepad.b
        if state.gamepad.bumper_right:
            # Turn to hub
            rotation = self.__pid(angle_to_hub)
            if self.__mode == MainCommand.Mode.TWO_CARGO:
                # with both intakes up in two cargo mode
                toggle_left_intake = not state.robot.intake_up(IntakeSide.LEFT)
                toggle_right_intake = not state.robot.intake_up(IntakeSide.RIGHT)
        elif state.gamepad.bumper_left:
            # Turn to cargo
            rotation = self.__pid(angle_to_nearest_cargo)
            if self.__mode == MainCommand.Mode.TWO_CARGO:
                # put nearby intake down and put far intake up in two cargo mode
                toggle_left_intake = state.robot.intake_up(IntakeSide.LEFT) == (
                        IntakeSide.LEFT == nearest_intake)
                toggle_right_intake = state.robot.intake_up(IntakeSide.RIGHT) == (
                        IntakeSide.RIGHT == nearest_intake)
        if self.__mode in [MainCommand.Mode.THREE_CARGO, MainCommand.Mode.ALL_CARGO]:
            # Keep both intakes down in all cargo mode
            toggle_left_intake = state.robot.intake_up(IntakeSide.LEFT)
            toggle_right_intake = state.robot.intake_up(IntakeSide.RIGHT)

        # Set controls
        controls.rotate = rotation
        controls.toggle_left_intake = toggle_left_intake
        controls.toggle_right_intake = toggle_right_intake
        return controls


class HoodCommand(Command):
    '''Automated control of the hood based on Eliot's angles'''
    def __init__(self):
        super().__init__()
        self.__pid = PID(0.100, 0.001, 0.000, setpoint=0, output_limits=(-4, 4))

    def execute(self, state: State, controls: Controls) -> Controls:
        '''Execute'''
        HOOD_ANGLES = [
            165,  155,  147,  145, 140,
            136,  127,  125,  120, 117,
            110,  107,  102,  99,  94,
            90,   86,   81,   77,  73,
            69,   65,   60,   41,  40,
            38,   35,   33,   31,  29,
            27,   25,   22.5, 20,  0
        ]
        distance_to_hub = state.distance_to_hub()
        hood_index = int((distance_to_hub - 1.3) * 10)
        hood_index = min(max(hood_index, 0), 34)
        target_hood_angle = HOOD_ANGLES[hood_index]
        hood_angle = state.robot.hood.local_rotation.x
        if hood_angle >= 270:
            hood_angle = (hood_angle - 450) * -1
        elif hood_angle <= 90:
            hood_angle = (hood_angle - 90) * -1
        # Use PID control for the hood angle
        angle_difference = target_hood_angle - hood_angle
        angle_output = self.__pid(angle_difference)

        controls.aim_up = angle_output < 0
        controls.aim_down = angle_output > 0
        controls.precision_left = True
        controls.precision_right = True
        controls.precision = abs(angle_output)
        return controls


class ClimberCommand(Command):
    '''Automated control of the climber'''
    def __init__(self):
        super().__init__()
        self.__pid = PID(-0.100, 0.000, 0.000, setpoint=0, output_limits=(-1, 1))

    def execute(self, state: State, controls: Controls) -> Controls:
        '''Execute'''

        # Extend arms when in hangar during endgame
        body_position = state.robot.body.global_position
        if state.game.phase not in [GamePhase.READY, GamePhase.ENDGAME, GamePhase.FINISHED]:
            # Keep arms retracted
            target_angle = 0
        elif ALLIANCE == Alliance.RED and body_position.x < -1.8 and body_position.z < -6.0:
            controls.climber_extend = True
            target_angle = 65
        elif ALLIANCE == Alliance.BLUE and body_position.x > 1.8 and body_position.z > 6.0:
            controls.climber_extend = True
            target_angle = 65
        else:
            # Keep arms retracted
            target_angle = 0

        # Control arm angle
        if controls.climber_forward < 0.5 and controls.climber_reverse < 0.5:
            if body_position.y > 0.25 and body_position.y < 0.75:
                # Auto climb until up
                controls.climber_forward = 1.0
            elif body_position.y < 0.625:
                # We use hook one but use similar logic to the dual intakes to move the nearest one
                hook_angle = state.robot.climber_hook_1.local_rotation.z
                if hook_angle > 180:
                    hook_angle -= 360
                if hook_angle < -90:
                    hook_angle += 180
                elif hook_angle > 90:
                    hook_angle -= 180
                error = target_angle - hook_angle
                control_output = self.__pid(error)
                if control_output > 0:
                    controls.climber_forward = control_output
                elif control_output < 0:
                    controls.climber_reverse = abs(control_output)

        return controls


if __name__ == '__main__':
    gamepad = Gamepad()
    main_command = MainCommand()
    hood_command = HoodCommand()
    climber_command = ClimberCommand()
    commands: list[Command] = [main_command, hood_command, climber_command]

    while True:
        start = time.time()
        with (open('GAME_STATE.txt', 'rt', encoding='UTF+8') as game_file,
                open('GameElements.txt', 'rt', encoding='UTF+8') as element_file,
                open('myRobot.txt', 'rt', encoding='UTF+8') as robot_file):
            state = State.read(game_file, element_file, robot_file, gamepad, ALLIANCE)
            if state is None:
                continue
            control_outputs = state.gamepad.default()
            for command in commands:
                control_outputs = command.execute(state, control_outputs)
            control_outputs.write()
        time.sleep(max((1 / FPS) - (time.time() - start), 0))
