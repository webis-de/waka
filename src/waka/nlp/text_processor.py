import abc
import logging
import time
from multiprocessing import Process, Queue
from typing import Optional, List, TypeVar, Generic

IN = TypeVar("IN")
OUT = TypeVar("OUT")


class TextProcessor(Generic[IN, OUT], metaclass=abc.ABCMeta):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Load...")

    @abc.abstractmethod
    def process(self, text: str, in_data: IN) -> Optional[List[OUT]]:
        # self.logger.debug(f"Process \"{in_data}\"")
        return None


class Pipeline(Generic[OUT], Process):
    processors: List[type[TextProcessor]]
    instances: List[TextProcessor]

    def __init__(self):
        super().__init__()
        self.in_queue = Queue()
        self.out_queue = Queue()
        self.processors = []
        self.eof_token = "<end>"
        self.instances = []

    def add_processor(self, processor: type[TextProcessor]):
        self.processors.append(processor)

    def process(self, text: str) -> None:
        self.in_queue.put(text)

    def run(self) -> None:
        for processor in self.processors:
            self.instances.append(processor())

        while True:
            try:
                text = self.in_queue.get()
            except KeyboardInterrupt:
                self.end()
                return

            if text == self.eof_token:
                return

            in_data = text
            out_data = None
            for processor in self.instances:
                start = time.time()
                out_data = processor.process(text, in_data)
                exec_time = time.time() - start

                processor.logger.debug(f"In: {type(in_data)}({len(in_data)}) [{exec_time:.4f}s]")
                in_data = out_data

            self.out_queue.put(out_data)

    def get(self) -> Optional[OUT]:
        return self.out_queue.get()

    def end(self):
        self.in_queue.put(self.eof_token)
