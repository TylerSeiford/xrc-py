from dataclasses import dataclass
from io import TextIOWrapper
import json
from models import Element, GameElementState


@dataclass
class ChargedUpGameElementState(GameElementState):
    '''Represents the current state of the rapid react game'''
    cones: list[Element]
    cubes: list[Element]
    misc: list[Element]

    @staticmethod
    def read(file: TextIOWrapper) -> 'ChargedUpGameElementState':
        '''Returns the current state of the game'''
        raw = file.read()
        raw = raw.strip()
        raw = json.loads(raw)
        elements: list[Element] = []
        for raw_object in raw['objects']:
            elements.append(Element.from_json(raw_object))
        cones: list[Element] = []
        cubes: list[Element] = []
        misc: list[Element] = []
        for element in elements:
            if element.element_type is None:
                misc.append(element)
            elif ChargedUpGameElementState.is_cone(element):
                cones.append(element)
            elif ChargedUpGameElementState.is_cube(element):
                cubes.append(element)
            else:
                misc.append(element)
        cones.sort(key=lambda i: i.identifier)
        cubes.sort(key=lambda i: i.identifier)
        return ChargedUpGameElementState(cones, cubes, misc)

    def __str__(self) -> str:
        return f"{[str(item) for item in self.cones]}\n" \
            f"{[str(item) for item in self.cubes]}\n" \
            f"{[str(item) for item in self.misc]}"

    @staticmethod
    def is_cone(element: Element) -> bool:
        return 'Cone' in element.name

    @staticmethod
    def is_cube(element: Element) -> bool:
        return 'Cube' in element.name
