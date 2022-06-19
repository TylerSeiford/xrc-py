from dataclasses import dataclass
from enum import Enum
from io import TextIOWrapper
import json
import math
from models import Element, Alliance, GameState, GamepadState, Gamepad, ControlOutput
from game_specific_models import GameElementState



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
class RobotState:
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
    def read(file: TextIOWrapper) -> 'RobotState':
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
        return RobotState(
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
class State:
    '''Represents the current state of everything'''
    robot: RobotState
    elements: GameElementState
    game: GameState
    gamepad: GamepadState
    __alliance: Alliance
    __distance_to_hub: float = None
    __angle_from_hub: float = None
    __angle_to_hub: float = None
    __alliance_cargo_in_robot: list[Element] = None
    __nearest_cargo: Element = None
    __nearest_cargo_info: tuple[float, float, IntakeSide] = None

    @staticmethod
    def read(game_file: TextIOWrapper, element_file: TextIOWrapper,
            robot_file: TextIOWrapper, gamepad: Gamepad,
            alliance: Alliance) -> 'State':
        '''Reads the current state from the files'''
        try:
            game_state = GameState.read(game_file)
            element_state = GameElementState.read(element_file)
            robot_state = RobotState.read(robot_file)
            gamepad_state = gamepad.read()
            return State(robot_state, element_state, game_state, gamepad_state, alliance)
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
            if self.__angle_to_hub < -180:
                self.__angle_to_hub += 360
            elif self.__angle_to_hub > 180:
                self.__angle_to_hub -= 360
        return self.__angle_to_hub

    def __alliance_cargo_search(self) -> None:
        '''Find the angle & distance to nearest cargo, nearest intake, and # of cargo in robot'''
        if self.__alliance == Alliance.BLUE:
            alliance_cargo = self.elements.blue_cargo
        else:
            alliance_cargo = self.elements.red_cargo
        nearest_distance = float('inf')
        nearest_vector = None
        nearest = None
        cargo_in_bot = []
        for cargo in alliance_cargo:
            difference = self.robot.body.global_position - cargo.global_position
            distance = math.hypot(difference.x, difference.y, difference.z)
            if distance < 0.4:
                # Cargo is in robot
                cargo_in_bot.append(cargo)
            elif difference.y < -0.5:
                pass # Cargo is too high
            elif distance < nearest_distance:
                nearest_distance = distance
                nearest_vector = difference
                nearest = cargo
        angle = math.degrees(math.atan2(nearest_vector.x, nearest_vector.z))
        angle = angle - self.robot.body.global_rotation.y
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
class Controls:
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
    def from_gamepad_state(gamepad: GamepadState) -> 'Controls':
        '''Returns the default controls'''
        return Controls(gamepad.a, gamepad.b, gamepad.x, gamepad.y,
                gamepad.dpad_down, gamepad.dpad_up, gamepad.dpad_right, gamepad.dpad_left,
                gamepad.bumper_left, gamepad.bumper_right,
                gamepad.start, gamepad.back,
                gamepad.right_y, gamepad.right_x,
                gamepad.left_y, gamepad.left_x,
                gamepad.trigger_left, gamepad.trigger_right)

    def write(self) -> None:
        '''Default controls for the robot'''
        return ControlOutput(self.reverse_intake, self.toggle_right_intake, self.toggle_left_intake,
                      self.shoot, self.aim_down, self.aim_up, self.climber_retract,
                      self.climber_extend, self.precision_left, self.precision_right,
                      self.stop, self.restart, self.right_y, self.rotate, self.forward_reverse,
                      self.strafe, self.climber_reverse, self.climber_forward, self.precision).write()



class Command:
    '''Represents a command to modify the controls for the robot'''
    def __init__(self):
        pass

    def execute(self, state: State, controls: Controls) -> Controls:
        '''Executes the command'''
        return controls
