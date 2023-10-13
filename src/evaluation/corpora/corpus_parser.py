import abc

from waka.nlp.kg import KnowledgeGraph


class CorpusParser(metaclass=abc.ABCMeta):
    def __init__(self, data_dir: str, train: bool = False, test: bool = True, dev: bool = True):
        self.data_dir = data_dir
        self.train = train
        self.test = test
        self.dev = dev

    @abc.abstractmethod
    def has_next(self) -> bool:
        pass

    @abc.abstractmethod
    def next(self) -> KnowledgeGraph:
        pass
