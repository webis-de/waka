import abc
from typing import Optional, List

from waka.nlp.kg import Entity, Triple


class TextProcessor(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def process(self, text: str) -> Optional[List[Entity | Triple]]:
        pass
