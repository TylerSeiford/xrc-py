from dataclasses import dataclass
from enum import Enum
from io import TextIOWrapper
import json
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
        return f"<{self.x}, {self.y}, {self.z}>"

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
    position: Vector
    rotation: Vector
    velocity: Vector | None
    angular_velocity: Vector | None

    @staticmethod
    def from_json(data: dict[str, any]) -> 'Element':
        '''Creates a game element from a JSON dictionary'''
        identifier = None
        element_type = None
        name = None
        position = None
        rotation = None
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
            position = Vector.from_json(data['global pos'])
        except KeyError:
            pass
        try:
            rotation = Vector.from_json(data['global rot'])
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
                position, rotation, velocity, angular_velocity)

    def __str__(self) -> str:
        return f"{self.name} @ {self.position}"


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


@dataclass
class RobotState:
    '''Represents the current state of a robot'''
    body: Element
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
        parts = []
        for element in elements:
            if element.name is None:
                parts.append(element)
            elif 'Body' in element.name:
                body = element
            else:
                parts.append(element)
        return RobotState(body, parts)

    def __str__(self) -> str:
        return f"Robot @ {self.body.position}"


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
    climber_a: float
    climber_b: float
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
            file.write(f"dpad_left={1 if self.climber_extend else 0}\n")
            file.write(f"dpad_right={1 if self.climber_retract else 0}\n")
            file.write(f"bumper_l={1 if self.precision_left else 0}\n")
            file.write(f"bumper_r={1 if self.precision_right else 0}\n")
            file.write(f"stop={1 if self.stop else 0}\n")
            file.write(f"restart={1 if self.restart else 0}\n")
            file.write(f"right_y={self.right_y}\n")
            file.write(f"right_x={self.rotate}\n")
            file.write(f"left_y={self.forward_reverse}\n")
            file.write(f"left_x={self.strafe}\n")
            file.write(f"trigger_l={self.climber_a}\n")
            file.write(f"trigger_r={self.climber_b}\n")
            file.write(f"precision={self.precision}\n")


class GamePhase(Enum):
    '''Represents the current phase of the game'''
    READY = 0
    AUTO = 1
    TELEOP = 2
    FINISHED = 3

    @staticmethod
    def from_str(string: str) -> 'GamePhase':
        '''Returns the GamePhase corresponding to the given string'''
        match(string.strip()):
            case 'READY': return GamePhase.READY
            case 'AUTO': return GamePhase.AUTO
            case 'TELEOP': return GamePhase.TELEOP
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


class Gamepad:
    '''Represents the gamepad'''
    def __init__(self, stick: int = 0):
        pygame.init()
        pygame.joystick.init()
        self.__joystick = pygame.joystick.Joystick(stick)

    def read(self) -> Controls:
        '''Reads the current controls from a joystick'''
        pygame.event.pump()
        a = self.__joystick.get_button(0)
        b = self.__joystick.get_button(1)
        x = self.__joystick.get_button(2)
        y = self.__joystick.get_button(3)
        dpad = self.__joystick.get_hat(0)
        dpad_down = dpad[1] == -1
        dpad_up = dpad[1] == 1
        dpad_left = dpad[0] == -1
        dpad_right = dpad[0] == 1
        bumper_left = self.__joystick.get_button(4)
        bumper_right = self.__joystick.get_button(5)
        restart = self.__joystick.get_button(8)
        stop = self.__joystick.get_button(7)
        right_y = self.__joystick.get_axis(3)
        right_x = self.__joystick.get_axis(2)
        left_y = self.__joystick.get_axis(1)
        left_x = self.__joystick.get_axis(0)
        trigger_left = 0
        trigger_right = 0
        return Controls(a, b, x, y,
                dpad_down, dpad_up, dpad_left, dpad_right,
                bumper_left, bumper_right, stop, restart,
                right_y, right_x, left_y, left_x,
                trigger_left, trigger_right)
