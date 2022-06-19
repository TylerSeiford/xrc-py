from dataclasses import dataclass
from io import TextIOWrapper
import json
from models import Element, GameElementState



@dataclass
class RapidReactGameElementState(GameElementState):
    '''Represents the current state of the rapid react game'''
    red_cargo: list[Element]
    blue_cargo: list[Element]
    misc: list[Element]

    @staticmethod
    def read(file: TextIOWrapper) -> 'RapidReactGameElementState':
        '''Returns the current state of the game'''
        raw = file.read()
        raw = raw.strip()
        raw = json.loads(raw)
        elements: list[Element] = []
        for raw_object in raw['objects']:
            elements.append(Element.from_json(raw_object))
        red_cargo: list[Element] = []
        blue_cargo: list[Element] = []
        misc: list[Element] = []
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
        return RapidReactGameElementState(red_cargo, blue_cargo, misc)

    def __str__(self) -> str:
        return f"{[str(item) for item in self.red_cargo]}\n" \
            f"{[str(item) for item in self.blue_cargo]}\n" \
            f"{[str(item) for item in self.misc]}"
