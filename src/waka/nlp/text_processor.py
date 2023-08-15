import abc
from typing import Optional, List, TypeVar, Generic

from waka.nlp.kg import Entity, Triple

IN = TypeVar("IN")
OUT = TypeVar("OUT")


class TextProcessor(Generic[IN, OUT], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def process(self, in_data: IN) -> Optional[List[OUT]]:
        pass


class Pipeline(Generic[OUT]):
    processors: List[TextProcessor]

    def __init__(self):
        self.processors = []

    def add_processor(self, processor: TextProcessor):
        self.processors.append(processor)

    def process(self, text: str) -> Optional[OUT]:
        in_data = text
        for processor in self.processors:
            out_data = processor.process(in_data)
            in_data = out_data

        return out_data
