from dataclasses import dataclass
from enum import Enum
from io import TextIOWrapper
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


class Alliance(Enum):
    '''Represents the alliance of the robot'''
    RED = 0
    BLUE = 1


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
class ControlOutput:
    '''Represents the control outputs to the game'''
    a: bool
    b: bool
    x: bool
    y: bool
    dpad_down: bool
    dpad_up: bool
    dpad_left: bool
    dpad_right: bool
    bumper_l: bool
    bumper_r: bool
    stop: bool
    restart: bool
    right_y: float
    right_x: float
    left_y: float
    left_x: float
    trigger_l: float
    trigger_r: float
    precision: float

    def write(self) -> None:
        '''Writes the current output to the game'''
        with open('Controls.txt', 'w', encoding='UTF+8') as file:
            file.write(f"a={1 if self.a else 0}\n")
            file.write(f"b={1 if self.b else 0}\n")
            file.write(f"x={1 if self.x else 0}\n")
            file.write(f"y={1 if self.y else 0}\n")
            file.write(f"dpad_down={1 if self.dpad_down else 0}\n")
            file.write(f"dpad_up={1 if self.dpad_up else 0}\n")
            file.write(f"dpad_left={1 if self.dpad_left else 0}\n")
            file.write(f"dpad_right={1 if self.dpad_right else 0}\n")
            file.write(f"bumper_l={1 if self.bumper_l else 0}\n")
            file.write(f"bumper_r={1 if self.bumper_r else 0}\n")
            file.write(f"stop={1 if self.stop else 0}\n")
            file.write(f"restart={1 if self.restart else 0}\n")
            file.write(f"right_y={self.right_y}\n")
            file.write(f"right_x={self.right_x}\n")
            file.write(f"left_y={self.left_y}\n")
            file.write(f"left_x={self.left_x}\n")
            file.write(f"trigger_l={self.trigger_l}\n")
            file.write(f"trigger_r={self.trigger_r}\n")
            file.write(f"precision={self.precision}\n")
