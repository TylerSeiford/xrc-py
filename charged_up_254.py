from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from io import TextIOWrapper
import json
import math
import time
from cached_pid import PID
from models import AutomationProvider, Command, Controls, Element, Alliance, GamePhase, GameState, GamepadState, Gamepad, ControlOutput, Logger, RobotInfo, RobotState, State, Util, Vector
from charged_up import ChargedUpGameElementState


@dataclass
class CU254RobotState(RobotState):
    '''Represents the current state of a robot'''
    body: Element
    not_updated: Element
    lift: Element
    slide: Element
    slide_2: Element
    intake_1: Element
    intake_2: Element
    intake_3: Element
    intake_4: Element
    lift_buddy: Element
    buddy_hinge: Element
    parts: list[Element]

    @staticmethod
    def read(file: TextIOWrapper) -> tuple['CU254RobotState', RobotInfo]:
        '''Returns the current state of the robot'''
        raw = file.read()
        raw = raw.strip()
        raw = json.loads(raw)
        elements: list[Element] = []
        robot_info: RobotInfo
        for raw_object in raw['myrobot']:
            element = Element.from_json(raw_object)
            if isinstance(element, RobotInfo):
                robot_info = element
            else:
                elements.append(element)
        body = None
        not_updated = None
        lift = None
        slide = None
        slide_2 = None
        intake_1 = None
        intake_2 = None
        intake_3 = None
        intake_4 = None
        lift_buddy = None
        buddy_hinge = None
        parts = []
        for element in elements:
            if element.name is None:
                parts.append(element)
            elif 'Body' in element.name:
                body = element
            elif 'NotUpdated' in element.name:
                not_updated = element
            elif 'Slide2' in element.name:
                slide_2 = element
            elif 'Slide' in element.name:
                slide = element
            elif 'Intake1' in element.name:
                intake_1 = element
            elif 'Intake2' in element.name:
                intake_2 = element
            elif 'Intake3' in element.name:
                intake_3 = element
            elif 'Intake4' in element.name:
                intake_4 = element
            elif 'LiftBuddy' in element.name:
                lift_buddy = element
            elif 'BuddyHinge' in element.name:
                buddy_hinge = element
            elif 'Lift' in element.name:
                lift = element
            else:
                parts.append(element)
        return CU254RobotState(
            body,
            not_updated,
            lift,
            slide, slide_2,
            intake_1, intake_2, intake_3, intake_4,
            lift_buddy, buddy_hinge,
            parts
        ), robot_info

    def __str__(self) -> str:
        return f"Robot @ {self.body.global_position}"


@dataclass
class CU254State(State):
    '''Represents the current state of everything'''
    robot: CU254RobotState
    elements: ChargedUpGameElementState
    game: GameState
    gamepad: GamepadState
    robot_info: RobotInfo
    _elements_in_intake: list[Element] = None

    @staticmethod
    def read(game_file: TextIOWrapper, element_file: TextIOWrapper,
             robot_file: TextIOWrapper, gamepad: Gamepad) -> 'CU254State':
        '''Reads the current state from the files'''
        try:
            game_state = GameState.read(game_file)
            element_state = ChargedUpGameElementState.read(element_file)
            robot_state, robot_info = CU254RobotState.read(robot_file)
            gamepad_state = gamepad.read()
            return CU254State(robot_state, element_state, game_state, gamepad_state, robot_info)
        except json.JSONDecodeError:
            return None  # Error reading file, try again
        except ValueError:
            return None  # Error reading file, try again

    def __element_search(self):
        body_position = self.robot.body.global_position
        body_rotation = self.robot.body.global_rotation
        nearest = Util.nearest_element(
            body_position,
            self.elements.cones + self.elements.cubes,
            0.0,
            -1.0
        )

        nearest_position = nearest.global_position
        delta = nearest_position - body_position
        lift_position = self.robot.lift.local_position
        slide_position = self.robot.slide.local_position
        slide_2_position = self.robot.slide_2.local_position
        intake_1_position = self.robot.intake_1.local_position
        intake_2_position = self.robot.intake_2.local_position
        intake_3_position = self.robot.intake_3.local_position
        intake_4_position = self.robot.intake_4.local_position
        intake_average_position = (intake_1_position + intake_2_position +
                           intake_3_position + intake_4_position) / 4
        intake_rotated_position = intake_average_position.rotate(body_rotation.y)
        lift_rotated_position = slide_position.rotate(body_rotation.y)
        slide_rotated_position = slide_position.rotate(body_rotation.y)
        slide_2_rotated_position = slide_2_position.rotate(body_rotation.y)
        guess_position = intake_rotated_position + slide_rotated_position + slide_2_rotated_position + lift_rotated_position
        Logger.log(
            f"{body_position.x},{body_position.y},{body_position.z},"
            f"{body_rotation.x},{body_rotation.y},{body_rotation.z},"
            f"{nearest_position.x},{nearest_position.y},{nearest_position.z},"
            f"{delta.x},{delta.y},{delta.z},{abs(delta)},"
            f"{lift_position.x},{lift_position.y},{lift_position.z},{abs(lift_position)},"
            f"{slide_position.x},{slide_position.y},{slide_position.z},{abs(slide_position)},"
            f"{slide_2_position.x},{slide_2_position.y},{slide_2_position.z},{abs(slide_2_position)},"
            f"{intake_1_position.x},{intake_1_position.y},{intake_1_position.z},{abs(intake_1_position)},"
            f"{intake_2_position.x},{intake_2_position.y},{intake_2_position.z},{abs(intake_2_position)},"
            f"{intake_3_position.x},{intake_3_position.y},{intake_3_position.z},{abs(intake_3_position)},"
            f"{intake_4_position.x},{intake_4_position.y},{intake_4_position.z},{abs(intake_4_position)},"
            f"{intake_average_position.x},{intake_average_position.y},{intake_average_position.z},{abs(intake_average_position)},"
            f"{intake_rotated_position.x},{intake_rotated_position.y},{intake_rotated_position.z},{abs(intake_rotated_position)},"
            f"{lift_rotated_position.x},{lift_rotated_position.y},{lift_rotated_position.z},{abs(lift_rotated_position)},"
            f"{slide_rotated_position.x},{slide_rotated_position.y},{slide_rotated_position.z},{abs(slide_rotated_position)},"
            f"{slide_2_rotated_position.x},{slide_2_rotated_position.y},{slide_2_rotated_position.z},{abs(slide_2_rotated_position)},"
            f"{guess_position.x},{guess_position.y},{guess_position.z},{abs(guess_position)},"
        )

        self._elements_in_intake = Util.elements_within(
            intake_average_position,
            self.elements.cones + self.elements.cubes,
            0.2
        )

    def elements_in_intake(self) -> list[Element]:
        if self._elements_in_intake is None:
            self.__element_search()
        return self._elements_in_intake


@dataclass
class CU254Controls(Controls):
    '''Represents the current controls for a robot'''
    reverse_intake: bool
    slide_out: bool
    slide_in: bool
    toggle_climb: bool
    stow_arm: bool
    station_arm: bool
    high_arm: bool
    mid_arm: bool
    bumper_left: bool
    bumper_right: bool
    stop: bool
    restart: bool
    right_y: float
    rotate: float
    forward_reverse: float
    strafe: float
    elevator_down: float
    elevator_up: float
    precision: float = 0.3

    @staticmethod
    def from_gamepad_state(gamepad: GamepadState) -> 'CU254Controls':
        '''Returns the default controls'''
        return CU254Controls(gamepad.a, gamepad.b, gamepad.x, gamepad.y,
                             gamepad.dpad_down, gamepad.dpad_up, gamepad.dpad_right, gamepad.dpad_left,
                             gamepad.bumper_left, gamepad.bumper_right,
                             gamepad.start, gamepad.back,
                             gamepad.right_y, gamepad.right_x,
                             gamepad.left_y, gamepad.left_x,
                             gamepad.trigger_left, gamepad.trigger_right)

    def write(self) -> None:
        '''Default controls for the robot'''
        return ControlOutput(
            self.reverse_intake, self.slide_out, self.slide_in,
            self.toggle_climb,
            self.stow_arm, self.station_arm,
            self.mid_arm, self.high_arm,
            self.bumper_left, self.bumper_right,
            self.stop, self.restart,
            self.right_y, self.rotate,
            self.forward_reverse, self.strafe,
            self.elevator_down, self.elevator_up,
            self.precision
        ).write()


class CU254Command(Command):
    '''Represents a command to modify the controls for the robot'''

    def __init__(self):
        pass

    def __call__(self, state: CU254State, controls: CU254Controls) -> CU254Controls:
        '''Executes the command'''
        return controls


class ArmCommand(CU254Command):
    '''Automated control of the arm'''

    class PlaceMode(Enum):
        '''Represents the mode'''
        HIGH = 0
        MID = 1
        LOW = 2

    class PickupMode(Enum):
        '''Represents the mode'''
        DOUBLE_SUBSTATION = 0
        GROUND = 1

    def __init__(self):
        super().__init__()
        self.__pid = PID(-5.000, 0.000, 0.000, setpoint=0,
                         output_limits=(-1, 1))
        self.__place_mode = ArmCommand.PlaceMode.LOW
        self.__dpad_up = False
        self.__pickup_mode = ArmCommand.PickupMode.DOUBLE_SUBSTATION
        self.__bumper_left = False
        self.__ground_override = False
        self.__bumper_right = False
        self.__cone = True
        self.__dpad_left = False

    def _in_loading_zone(self, alliance: Alliance, position: Vector) -> bool:
        match (alliance):
            case Alliance.RED:
                if position.z > 2 and position.x > 3.15:
                    return True
                if position.z > 5.3 and position.x > 1.7:
                    return True
                return False
            case Alliance.BLUE:
                if position.z < -2 and position.x > 3.15:
                    return True
                if position.z < -5.3 and position.x > 1.7:
                    return True
                return False
            case _:
                return False

    def _in_community(self, alliance: Alliance, position: Vector) -> bool:
        match (alliance):
            case Alliance.RED:
                if position.z < -3.8 and position.x < -2.8:
                    return True
                if position.z < -5.0 and position.x < 0.4:
                    return True
                if position.z < -5.3 and position.x < 1.1 and position.x > 0.4:
                    return True
                return False
            case Alliance.BLUE:
                if position.z > 3.8 and position.x < -2.8:
                    return True
                if position.z > 5.0 and position.x < 0.4:
                    return True
                if position.z > 5.3 and position.x < 1.1 and position.x > 0.4:
                    return True
                return False
            case _:
                return False

    def _ground_pickup(self) -> tuple[float, float]:
        return 0.000, 0.332

    def _stow(self) -> tuple[float, float]:
        return 0.130, 0.287

    def _double_substation(self) -> tuple[float, float]:
        return 0.858, 0.343

    def _high(self, cone: bool, cube: bool) -> tuple[float, float]:
        if cone:
            return 0.978, 0.424
        elif cube:
            return 0.811, 0.378
        else:
            return self._ground_pickup()

    def _mid(self, cone: bool, cube: bool) -> tuple[float, float]:
        if cone:
            return 0.811, 0.378
        elif cube:
            return 0.590, 0.325
        else:
            return self._ground_pickup()

    def _low(self, cone: bool, cube: bool) -> tuple[float, float]:
        if cone:
            return 0.140, 0.332
        elif cube:
            return 0.140, 0.332
        else:
            return self._ground_pickup()

    def __call__(self, state: CU254State, controls: CU254Controls) -> CU254Controls:
        '''Execute'''
        # Update modes
        if state.gamepad.dpad_up:
            if not self.__dpad_up:
                match self.__place_mode:
                    case ArmCommand.PlaceMode.HIGH:
                        self.__place_mode = ArmCommand.PlaceMode.LOW
                    case ArmCommand.PlaceMode.MID:
                        self.__place_mode = ArmCommand.PlaceMode.HIGH
                    case ArmCommand.PlaceMode.LOW:
                        self.__place_mode = ArmCommand.PlaceMode.MID
                print(f"Switching to {self.__place_mode.name}")
                self.__dpad_up = True
        else:
            if self.__dpad_up:
                self.__dpad_up = False
        if state.gamepad.bumper_left:
            if not self.__bumper_left:
                match self.__pickup_mode:
                    case ArmCommand.PickupMode.DOUBLE_SUBSTATION:
                        self.__pickup_mode = ArmCommand.PickupMode.GROUND
                    case ArmCommand.PickupMode.GROUND:
                        self.__pickup_mode = ArmCommand.PickupMode.DOUBLE_SUBSTATION
                print(f"Switching to {self.__pickup_mode.name}")
                self.__bumper_left = True
        else:
            if self.__bumper_left:
                self.__bumper_left = False
        if state.gamepad.bumper_right:
            if not self.__bumper_right:
                if self.__ground_override:
                    self.__ground_override = False
                    print('Disabling GROUND OVERRIDE')
                else:
                    self.__ground_override = True
                    print('Enabling GROUND OVERRIDE')
                self.__bumper_right = True
        else:
            if self.__bumper_right:
                self.__bumper_right = False
        if state.gamepad.dpad_left:
            if not self.__dpad_left:
                if self.__cone:
                    self.__cone = False
                    print('CUBE')
                else:
                    self.__cone = True
                    print('CONE')
                self.__dpad_left = True
        else:
            if self.__dpad_left:
                self.__dpad_left = False

        # See what element we have (TODO)
        state.elements_in_intake()
        cone = self.__cone
        cube = not cone

        body_position = state.robot.body.global_position
        target_elevator = 0
        target_slider = 0

        if self.__ground_override:
            # Override to intake from ground
            target_elevator, target_slider = self._ground_pickup()
        else:
            if self._in_loading_zone(state.robot_info.alliance, body_position):
                # Go to pickup position when in the loading zone
                match self.__pickup_mode:
                    case ArmCommand.PickupMode.DOUBLE_SUBSTATION:
                        target_elevator, target_slider = self._double_substation()
                    case ArmCommand.PickupMode.GROUND:
                        target_elevator, target_slider = self._ground_pickup()
            elif self._in_community(state.robot_info.alliance, body_position):
                # Go to placement position when in community
                match self.__place_mode:
                    case ArmCommand.PlaceMode.HIGH:
                        target_elevator, target_slider = self._high(cone, cube)
                    case ArmCommand.PlaceMode.MID:
                        target_elevator, target_slider = self._mid(cone, cube)
                    case ArmCommand.PlaceMode.LOW:
                        target_elevator, target_slider = self._low(cone, cube)
            else:
                # Stay stowed when outside
                target_elevator, target_slider = self._stow()

        # Control elevator position
        elevator_height = state.robot.lift.local_position.y
        if controls.elevator_up < 0.5 and controls.elevator_down < 0.5:
            error = target_elevator - elevator_height
            control_output = self.__pid(error)
            if control_output > 0:
                controls.elevator_up = control_output
            elif control_output < 0:
                controls.elevator_down = abs(control_output)

        # Control slider position
        slider_height = state.robot.slide_2.local_position.y - elevator_height
        if not controls.slide_out and not controls.slide_in:
            error = target_slider - slider_height
            if error > 0.01:
                controls.slide_out = True
                controls.slide_in = False
            elif error < -0.01:
                controls.slide_out = False
                controls.slide_in = True

        controls.high_arm = False
        controls.mid_arm = False
        controls.stow_arm = False
        controls.station_arm = False
        # print(f"{elevator_height:.3f} {slider_height:.3f}")
        return controls


class CU254AutomationProvider(AutomationProvider):
    '''Automated control of the Rapid React 67 robot'''

    def __init__(self):
        super().__init__()
        self.__commands: tuple[CU254Command] = (
            ArmCommand(),
        )

    def __call__(self, game_file: TextIOWrapper, element_file: TextIOWrapper,
                 robot_file: TextIOWrapper, gamepad: Gamepad) -> None:
        '''Execute'''
        state = CU254State.read(game_file, element_file, robot_file, gamepad)
        if state is None:
            return
        control_outputs = CU254Controls.from_gamepad_state(state.gamepad)
        for command in self.__commands:
            control_outputs = command(state, control_outputs)
        control_outputs.write()
