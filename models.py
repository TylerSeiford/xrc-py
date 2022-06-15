from dataclasses import dataclass
from enum import Enum
from io import TextIOWrapper
import json
import math
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = ''
import pygame



@dataclass
class Vector:
    '''Represents a vector in 3D space'''
    x: float
    y: float
    z: float

    @staticmethod
    def from_json(data: list[float]) -> 'Vector':
        '''Creates a vector from a list of 3 floats'''
        return Vector(data[0], data[1], data[2])

    def __str__(self) -> str:
        return f"<{self.x:.3f}, {self.y:.3f}, {self.z:.3f}>"

    def __add__(self, other: 'Vector') -> 'Vector':
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector') -> 'Vector':
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __pos__(self) -> 'Vector':
        return Vector(+self.x, +self.y, +self.z)

    def __neg__(self) -> 'Vector':
        return Vector(-self.x, -self.y, -self.z)

    def __abs__(self) -> float:
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5


@dataclass
class Element:
    '''Represents a game element'''
    identifier: int
    element_type: int
    name: str
    global_position: Vector
    global_rotation: Vector
    local_position: Vector
    local_rotation: Vector
    velocity: Vector | None
    angular_velocity: Vector | None

    @staticmethod
    def from_json(data: dict[str, any]) -> 'Element':
        '''Creates a game element from a JSON dictionary'''
        identifier = None
        element_type = None
        name = None
        global_position = None
        global_rotation = None
        local_position = None
        local_rotation = None
        velocity = None
        angular_velocity = None
        try:
            identifier = data['id']
        except KeyError:
            pass
        try:
            element_type = data['type']
        except KeyError:
            pass
        try:
            name = data['name']
        except KeyError:
            pass
        try:
            global_position = Vector.from_json(data['global pos'])
        except KeyError:
            pass
        try:
            global_rotation = Vector.from_json(data['global rot'])
        except KeyError:
            pass
        try:
            local_position = Vector.from_json(data['local pos'])
        except KeyError:
            pass
        try:
            local_rotation = Vector.from_json(data['local rot'])
        except KeyError:
            pass
        try:
            velocity = Vector.from_json(data['velocity'])
        except KeyError:
            pass
        try:
            angular_velocity = Vector.from_json(data['rot velocity'])
        except KeyError:
            pass
        return Element(identifier, element_type, name,
                global_position, global_rotation, local_position, local_rotation,
                velocity, angular_velocity)

    def __str__(self) -> str:
        return f"{self.name} @ {self.global_position}"


@dataclass
class GameElementState:
    '''Represents the current state of the game'''
    red_cargo: list[Element]
    blue_cargo: list[Element]
    misc : list[Element]

    @staticmethod
    def read(file: TextIOWrapper) -> 'GameElementState':
        '''Returns the current state of the game'''
        raw = file.read()
        raw = raw.strip()
        raw = json.loads(raw)
        elements = []
        for raw_object in raw['objects']:
            elements.append(Element.from_json(raw_object))
        red_cargo = []
        blue_cargo = []
        misc = []
        for element in elements:
            if element.element_type is None:
                misc.append(element)
            elif 'Ball_Red' in element.name:
                red_cargo.append(element)
            elif 'Ball_Blue' in element.name:
                blue_cargo.append(element)
            else:
                misc.append(element)
        red_cargo.sort(key=lambda i: i.identifier)
        blue_cargo.sort(key=lambda i: i.identifier)
        return GameElementState(red_cargo, blue_cargo, misc)

    def __str__(self) -> str:
        return f"{[str(item) for item in self.red_cargo]}\n" \
            f"{[str(item) for item in self.blue_cargo]}\n" \
            f"{[str(item) for item in self.misc]}"


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
        elements = []
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


class Alliance(Enum):
    '''Represents the alliance of the robot'''
    RED = 0
    BLUE = 1


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

    def write(self) -> None:
        '''Writes the current controls to the game'''
        with open('Controls.txt', 'w', encoding='UTF+8') as file:
            file.write(f"a={1 if self.reverse_intake else 0}\n")
            file.write(f"b={1 if self.toggle_right_intake else 0}\n")
            file.write(f"x={1 if self.toggle_left_intake else 0}\n")
            file.write(f"y={1 if self.shoot else 0}\n")
            file.write(f"dpad_down={1 if self.aim_down else 0}\n")
            file.write(f"dpad_up={1 if self.aim_up else 0}\n")
            file.write(f"dpad_left={1 if self.climber_retract else 0}\n")
            file.write(f"dpad_right={1 if self.climber_extend else 0}\n")
            file.write(f"bumper_l={1 if self.precision_left else 0}\n")
            file.write(f"bumper_r={1 if self.precision_right else 0}\n")
            file.write(f"stop={1 if self.stop else 0}\n")
            file.write(f"restart={1 if self.restart else 0}\n")
            file.write(f"right_y={self.right_y}\n")
            file.write(f"right_x={self.rotate}\n")
            file.write(f"left_y={self.forward_reverse}\n")
            file.write(f"left_x={self.strafe}\n")
            file.write(f"trigger_l={self.climber_reverse}\n")
            file.write(f"trigger_r={self.climber_forward}\n")
            file.write(f"precision={self.precision}\n")


class GamePhase(Enum):
    '''Represents the current phase of the game'''
    READY = 0
    AUTO = 1
    TELEOP = 2
    ENDGAME = 3
    FINISHED = 4

    @staticmethod
    def from_str(string: str) -> 'GamePhase':
        '''Returns the GamePhase corresponding to the given string'''
        match(string.strip()):
            case 'READY': return GamePhase.READY
            case 'AUTO': return GamePhase.AUTO
            case 'TELEOP': return GamePhase.TELEOP
            case 'ENDGAME': return GamePhase.ENDGAME
            case 'FINISHED': return GamePhase.FINISHED
            case _: raise ValueError(f"{string} is not a valid GamePhase")


@dataclass
class GameState:
    '''Represents the current state of the game'''
    phase: GamePhase
    time_left: float

    @staticmethod
    def read(file: TextIOWrapper) -> 'GameState':
        '''Returns the current state of the game'''
        phase = file.readline()
        timestamp = file.readline()
        phase = GamePhase.from_str(phase)
        timestamp = timestamp.split('=')[1].strip()
        timestamp = float(timestamp)
        return GameState(phase, timestamp)

    def __str__(self) -> str:
        return f"{self.phase} {self.time_left}"


@dataclass
class GamepadState:
    '''Represents the current state of the gamepad'''
    a: bool
    b: bool
    x: bool
    y: bool
    dpad_down: bool
    dpad_up: bool
    dpad_left: bool
    dpad_right: bool
    bumper_right: bool
    bumper_left: bool
    back: bool
    start: bool
    right_y: float
    right_x: float
    left_y: float
    left_x: float
    trigger_left: float
    trigger_right: float

    def default(self) -> Controls:
        '''Returns the default controls'''
        return Controls(self.a, self.b, self.x, self.y,
                self.dpad_down, self.dpad_up, self.dpad_right, self.dpad_left,
                self.bumper_left, self.bumper_right,
                self.start, self.back,
                self.right_y, self.right_x,
                self.left_y, self.left_x,
                self.trigger_left, self.trigger_right)


class Gamepad:
    '''Represents the gamepad'''
    def __init__(self, stick: int = 0):
        try:
            pygame.init()
            pygame.joystick.init()
            self.__joystick = pygame.joystick.Joystick(stick)
            print(f"Detected '{self.__joystick.get_name()}'")
        except pygame.error:
            print("No gamepad detected")
            self.__joystick = None

    def read(self) -> GamepadState:
        '''Reads the current state from a joystick'''
        if self.__joystick is None:
            return GamepadState(
                    False, False, False, False,
                    False, False, False, False,
                    False, False, False, False,
                    0, 0,
                    0, 0,
                    0, 0
            )
        pygame.event.pump()
        dpad = self.__joystick.get_hat(0)
        return GamepadState(
            a=self.__joystick.get_button(0),
            b=self.__joystick.get_button(1),
            x=self.__joystick.get_button(2),
            y=self.__joystick.get_button(3),
            dpad_down=dpad[1] == -1,
            dpad_up=dpad[1] == 1,
            dpad_left=dpad[0] == -1,
            dpad_right=dpad[0] == 1,
            bumper_right=self.__joystick.get_button(5),
            bumper_left=self.__joystick.get_button(4),
            back=self.__joystick.get_button(6),
            start=self.__joystick.get_button(7),
            right_y=self.__joystick.get_axis(3),
            right_x=self.__joystick.get_axis(2),
            left_y=self.__joystick.get_axis(1),
            left_x=self.__joystick.get_axis(0),
            trigger_left=(self.__joystick.get_axis(4) + 1) / 2,
            trigger_right=(self.__joystick.get_axis(5) + 1) / 2
        )


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


class Command:
    '''Represents a command to modify the controls for the robot'''
    def __init__(self):
        pass

    def execute(self, state: State, controls: Controls) -> Controls:
        '''Executes the command'''
        return controls
