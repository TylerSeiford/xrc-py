from dataclasses import dataclass
from enum import Enum
from io import TextIOWrapper
import json
import math
import time
from simple_pid import PID
from models import AutomationProvider, Command, Controls, Element, Alliance, GamePhase, GameState, GamepadState, Gamepad, ControlOutput, RobotState, State, Util
from rapid_react import RapidReactGameElementState



THREE_CARGO_TIME_LIMIT: float = 1.625



class IntakeSide(Enum):
    '''Represents the side of intake'''
    LEFT = 0
    RIGHT = 1


class IntakePosition(Enum):
    '''Represents the position'''
    UP = 0
    UNKNOWN = 1
    DOWN = 2

    @staticmethod
    def from_y(y: float) -> 'IntakePosition':
        '''Returns the position from a y coordinate'''
        if y > 0.45:
            return IntakePosition.UP
        if y < 0.4:
            return IntakePosition.DOWN
        return IntakePosition.UNKNOWN

    def __invert__(self):
        match(self):
            case IntakePosition.UP: return IntakePosition.DOWN
            case IntakePosition.DOWN: return IntakePosition.UP
            case IntakePosition.UNKNOWN: return IntakePosition.UNKNOWN


@dataclass
class RR67RobotState(RobotState):
    '''Represents the current state of a robot'''
    body: Element
    hood: Element
    left_intake: Element
    right_intake: Element
    climber_arm_1: Element
    climber_arm_2: Element
    climber_hook_1: Element
    climber_hook_2: Element
    parts: list[Element]

    @staticmethod
    def read(file: TextIOWrapper) -> 'RR67RobotState':
        '''Returns the current state of the robot'''
        raw = file.read()
        raw = raw.strip()
        raw = json.loads(raw)
        elements: list[Element] = []
        for raw_object in raw['myrobot']:
            elements.append(Element.from_json(raw_object))
        body = None
        hood = None
        left_intake = None
        right_intake = None
        climber_arm_1 = None
        climber_arm_2 = None
        climber_hook_1 = None
        climber_hook_2 = None
        parts = []
        for element in elements:
            if element.name is None:
                parts.append(element)
            elif 'Body' in element.name:
                body = element
            elif 'Indicator' in element.name:
                hood = element
            elif 'IntakeFlap1' in element.name:
                left_intake = element
            elif 'IntakeFlap2' in element.name:
                right_intake = element
            elif 'arm1' in element.name:
                climber_arm_1 = element
            elif 'arm2' in element.name:
                climber_arm_2 = element
            elif 'Hook1' in element.name:
                climber_hook_1 = element
            elif 'Hook2' in element.name:
                climber_hook_2 = element
            else:
                parts.append(element)
        return RR67RobotState(
            body, hood,
            left_intake, right_intake,
            climber_arm_1, climber_arm_2,
            climber_hook_1, climber_hook_2,
            parts
        )

    def intake_position(self, side: IntakeSide) -> IntakePosition:
        '''Returns the position of the intake'''
        if side is IntakeSide.LEFT:
            return IntakePosition.from_y(self.left_intake.local_position.y)
        return IntakePosition.from_y(self.right_intake.local_position.y)

    def __str__(self) -> str:
        return f"Robot @ {self.body.global_position}"


@dataclass
class RR67State(State):
    '''Represents the current state of everything'''
    robot: RR67RobotState
    elements: RapidReactGameElementState
    game: GameState
    gamepad: GamepadState
    alliance: Alliance
    __distance_to_hub: float = None
    __angle_from_hub: float = None
    __angle_to_hub: float = None
    __alliance_cargo_in_robot: list[Element] = None
    __nearest_cargo: Element = None
    __nearest_cargo_info: tuple[float, float, IntakeSide] = None

    @staticmethod
    def read(game_file: TextIOWrapper, element_file: TextIOWrapper,
            robot_file: TextIOWrapper, gamepad: Gamepad,
            alliance: Alliance) -> 'RR67State':
        '''Reads the current state from the files'''
        try:
            game_state = GameState.read(game_file)
            element_state = RapidReactGameElementState.read(element_file)
            robot_state = RR67RobotState.read(robot_file)
            gamepad_state = gamepad.read()
            return RR67State(robot_state, element_state, game_state, gamepad_state, alliance)
        except json.JSONDecodeError:
            return None # Error reading file, try again
        except ValueError:
            return None # Error reading file, try again

    def distance_to_hub(self) -> float:
        '''Returns the distance to the hub'''
        if self.__distance_to_hub is None:
            self.__distance_to_hub = math.hypot(
                    self.robot.body.global_position.x,
                    self.robot.body.global_position.z
            )
        return  self.__distance_to_hub

    def angle_from_hub(self) -> float:
        '''Returns the angle from the hub to the robot'''
        if self.__angle_from_hub is None:
            self.__angle_from_hub = math.degrees(math.atan2(self.robot.body.global_position.x,
                    self.robot.body.global_position.z))
        return self.__angle_from_hub

    def angle_to_hub(self) -> float:
        '''Returns the angle to the hub from the robot'''
        if self.__angle_to_hub is None:
            self.__angle_to_hub = self.angle_from_hub() - self.robot.body.global_rotation.y + 90
            self.__angle_to_hub = Util.fix_angle(self.__angle_to_hub)
        return self.__angle_to_hub

    def __alliance_cargo_search(self) -> None:
        '''Find the angle & distance to nearest cargo, nearest intake, and # of cargo in robot'''
        if self.alliance == Alliance.BLUE:
            alliance_cargo = self.elements.blue_cargo
        else:
            alliance_cargo = self.elements.red_cargo
        nearest_distance = float('inf')
        nearest = Util.nearest_element(
            self.robot.body.global_position, alliance_cargo,
            0.4, -0.5
        )
        cargo_in_bot = Util.elements_within(
            self.robot.body.global_position,
            self.elements.blue_cargo + self.elements.red_cargo,
            0.4
        )
        nearest_vector = self.robot.body.global_position - nearest.global_position
        angle = math.degrees(math.atan2(nearest_vector.x, nearest_vector.z))
        angle = angle - self.robot.body.global_rotation.y
        angle = Util.fix_angle(angle)

        # Wrap angle for dual intakes
        if angle > 90:
            angle -= 180
            intake = IntakeSide.LEFT
        elif angle < -90:
            angle += 180
            intake = IntakeSide.LEFT
        else:
            intake = IntakeSide.RIGHT
        self.__nearest_cargo = nearest
        self.__nearest_cargo_info = (angle, nearest_distance, intake)
        self.__alliance_cargo_in_robot = cargo_in_bot

    def cargo_in_robot(self) -> list[Element]:
        '''Returns the cargo in the robot'''
        if self.__alliance_cargo_in_robot is None:
            self.__alliance_cargo_search()
        return self.__alliance_cargo_in_robot

    def nearest_cargo(self) -> Element:
        '''Returns the nearest cargo'''
        if self.__nearest_cargo is None:
            self.__alliance_cargo_search()
        return self.__nearest_cargo

    def nearest_cargo_info(self) -> tuple[float, float, IntakeSide]:
        '''Returns the angle to, distance to, and intake closest to the nearest cargo'''
        if self.__nearest_cargo_info is None:
            self.__alliance_cargo_search()
        return self.__nearest_cargo_info


@dataclass
class RR67Controls(Controls):
    '''Represents the current controls for a robot'''
    reverse_intake: bool
    toggle_right_intake: bool
    toggle_left_intake: bool
    shoot: bool
    aim_down: bool
    aim_up: bool
    climber_extend: bool
    climber_retract: bool
    precision_left: bool
    precision_right: bool
    stop: bool
    restart: bool
    right_y: float
    rotate: float
    forward_reverse: float
    strafe: float
    climber_reverse: float
    climber_forward: float
    precision: float = 0.3

    @staticmethod
    def from_gamepad_state(gamepad: GamepadState) -> 'RR67Controls':
        '''Returns the default controls'''
        return RR67Controls(gamepad.a, gamepad.b, gamepad.x, gamepad.y,
                gamepad.dpad_down, gamepad.dpad_up, gamepad.dpad_right, gamepad.dpad_left,
                gamepad.bumper_left, gamepad.bumper_right,
                gamepad.start, gamepad.back,
                gamepad.right_y, gamepad.right_x,
                gamepad.left_y, gamepad.left_x,
                gamepad.trigger_left, gamepad.trigger_right)

    def write(self) -> None:
        '''Default controls for the robot'''
        return ControlOutput(
            self.reverse_intake, self.toggle_right_intake, self.toggle_left_intake,
            self.shoot,
            self.aim_down, self.aim_up,
            self.climber_retract, self.climber_extend,
            self.precision_left, self.precision_right,
            self.stop, self.restart,
            self.right_y, self.rotate,
            self.forward_reverse, self.strafe,
            self.climber_reverse, self.climber_forward,
            self.precision
        ).write()


class RR67Command(Command):
    '''Represents a command to modify the controls for the robot'''
    def __init__(self):
        pass

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
        '''Executes the command'''
        return controls



class TranslationCommand(RR67Command):
    '''Automated control of rotation'''

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
        '''Execute'''
        if not state.gamepad.bumper_left or abs(state.gamepad.left_x) > 0.1:
            return controls

        (angle_to_nearest_cargo, distance_to_nearest_cargo,
                nearest_intake) = state.nearest_cargo_info()
        if abs(angle_to_nearest_cargo) > 30 or distance_to_nearest_cargo < 0.625:
            return controls

        if nearest_intake == IntakeSide.LEFT:
            controls.strafe = -1.0
        elif nearest_intake == IntakeSide.RIGHT:
            controls.strafe = 1.0
        return controls


class RotationCommand(RR67Command):
    '''Automated control of rotation'''

    def __init__(self):
        super().__init__()
        self.__pid = PID(-0.022, -0.000, -0.002, setpoint=0, output_limits=(-1, 1))

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
        '''Execute'''
        # Gather data
        angle_to_hub = state.angle_to_hub()
        angle_to_nearest_cargo, _, _ = state.nearest_cargo_info()

        # Determine controls
        rotation = state.gamepad.right_x
        if state.gamepad.bumper_right:
            # Turn to hub
            rotation = self.__pid(angle_to_hub)
        elif state.gamepad.bumper_left:
            # Turn to cargo
            rotation = self.__pid(angle_to_nearest_cargo)

        # Set controls
        controls.rotate = rotation
        return controls


class IntakeCommand(RR67Command):
    '''Automated control of intake'''

    class Mode(Enum):
        '''Represents the mode'''
        TWO_CARGO = 2
        THREE_CARGO = 3

    def __init__(self):
        super().__init__()
        self.__mode = IntakeCommand.Mode.THREE_CARGO

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
        '''Execute'''
        # Gather data
        _, _, nearest_intake = state.nearest_cargo_info()

        # Update mode
        if state.gamepad.dpad_up and self.__mode != IntakeCommand.Mode.THREE_CARGO:
            self.__mode = IntakeCommand.Mode.THREE_CARGO
            print(f"Switching to {self.__mode.name}")
        elif state.gamepad.dpad_down and self.__mode != IntakeCommand.Mode.TWO_CARGO:
            self.__mode = IntakeCommand.Mode.TWO_CARGO
            print(f"Switching to {self.__mode.name}")

        # Determine controls
        target_left_intake = IntakePosition.UNKNOWN
        target_right_intake = IntakePosition.UNKNOWN
        if self.__mode == IntakeCommand.Mode.TWO_CARGO:
            # Keep both intakes up when aiming and only nearby intake down when intaking
            if state.gamepad.bumper_right:
                target_left_intake = IntakePosition.UP
                target_right_intake = IntakePosition.UP
            elif state.gamepad.bumper_left:
                if nearest_intake == IntakeSide.LEFT:
                    target_left_intake = IntakePosition.DOWN
                    target_right_intake = IntakePosition.UP
                elif nearest_intake == IntakeSide.RIGHT:
                    target_left_intake = IntakePosition.UP
                    target_right_intake = IntakePosition.DOWN
        elif self.__mode == IntakeCommand.Mode.THREE_CARGO:
            # Keep both intakes down in three cargo mode
            target_left_intake = IntakePosition.DOWN
            target_right_intake = IntakePosition.DOWN
        body_position = state.robot.body.global_position
        if state.game.phase in [GamePhase.READY, GamePhase.ENDGAME, GamePhase.FINISHED]:
            # Keep both intakes up in the hangar in endgame
            if (state.alliance == Alliance.RED
                    and body_position.x < -0.875 and body_position.z < -4.5):
                target_left_intake = IntakePosition.UP
                target_right_intake = IntakePosition.UP
            elif (state.alliance == Alliance.BLUE
                    and body_position.x > 0.875 and body_position.z > 4.5):
                target_left_intake = IntakePosition.UP
                target_right_intake = IntakePosition.UP


        # Allow manual override to opposite position while held
        if target_left_intake != IntakePosition.UNKNOWN and state.gamepad.x:
            target_left_intake = ~target_left_intake
        if target_right_intake != IntakePosition.UNKNOWN and state.gamepad.b:
            target_right_intake = ~target_right_intake

        # Set controls
        if target_left_intake != IntakePosition.UNKNOWN:
            controls.toggle_left_intake = (
                    target_left_intake != state.robot.intake_position(IntakeSide.LEFT))
        if target_right_intake != IntakePosition.UNKNOWN:
            controls.toggle_right_intake = (
                    target_right_intake != state.robot.intake_position(IntakeSide.RIGHT))
        return controls


class ShooterCommand(RR67Command):
    '''Automated control of shooter'''

    def __init__(self):
        super().__init__()
        self.__three_cargo_start = None
        self.__bypass_enabled = False

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
        '''Execute'''
        # Gather data
        cargo_in_robot = len(state.cargo_in_robot())

        # Read controls
        if state.gamepad.right_y < -0.9375 and not self.__bypass_enabled:
            print('Bypassing cargo limit')
            self.__bypass_enabled = True
        elif state.gamepad.right_y > 0.25 and self.__bypass_enabled:
            print('Disabling bypass')
            self.__bypass_enabled = False

        # Update cargo data
        if self.__three_cargo_start is None:
            if cargo_in_robot >= 3:
                self.__three_cargo_start = time.time()
        else:
            if cargo_in_robot < 3:
                self.__three_cargo_start = None
            else:
                time_left = THREE_CARGO_TIME_LIMIT - (time.time() - self.__three_cargo_start)
                if time_left < 0.25 and not self.__bypass_enabled:
                    # Shoot cargo to avoid penalty
                    controls.shoot = True
        return controls


class HoodCommand(RR67Command):
    '''Automated control of the hood based on Eliot's angles'''
    def __init__(self):
        super().__init__()
        self.__pid = PID(0.100, 0.001, 0.000, setpoint=0, output_limits=(-4, 4))

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
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


class ClimberCommand(RR67Command):
    '''Automated control of the climber'''
    def __init__(self):
        super().__init__()
        self.__pid = PID(-0.100, 0.000, 0.000, setpoint=0, output_limits=(-1, 1))

    def __call__(self, state: RR67State, controls: RR67Controls) -> RR67Controls:
        '''Execute'''
        # Extend arms when in hangar during endgame
        body_position = state.robot.body.global_position
        if state.game.phase in [GamePhase.READY, GamePhase.ENDGAME, GamePhase.FINISHED]:
            if (state.alliance == Alliance.RED
                and body_position.x < -0.875 and body_position.z < -4.5):
                target_angle = 65
                controls.climber_extend = True
            elif (state.alliance == Alliance.BLUE
                  and body_position.x > 0.875 and body_position.z > 4.5):
                target_angle = 65
                controls.climber_extend = True
            else:
                target_angle = 0
                controls.climber_retract = True
        else:
            # Keep arms retracted
            controls.climber_retract = True
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



class RR67AutomationProvider(AutomationProvider):
    '''Automated control of the Rapid React 67 robot'''

    def __init__(self):
        super().__init__()
        self.__commands: tuple[RR67Command] = (
            TranslationCommand(),
            RotationCommand(),
            IntakeCommand(),
            ShooterCommand(),
            HoodCommand(),
            ClimberCommand()
        )

    def __call__(self, game_file: TextIOWrapper, element_file: TextIOWrapper,
            robot_file: TextIOWrapper, gamepad: Gamepad,
            alliance: Alliance) -> None:
        '''Execute'''
        state = RR67State.read(game_file, element_file, robot_file, gamepad, alliance)
        if state is None:
            return
        control_outputs = RR67Controls.from_gamepad_state(state.gamepad)
        for command in self.__commands:
            control_outputs = command(state, control_outputs)
        control_outputs.write()
