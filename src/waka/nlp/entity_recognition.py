import abc
import logging
import os
from enum import Enum
from typing import List

import spacy
import sparknlp
import stanza
from sparknlp.pretrained import PretrainedPipeline

from waka.nlp.kg import Entity
from waka.nlp.text_processor import TextProcessor


class EntityType(Enum):
    ENTITY = 1
    LITERAL = 2


class EntityRecognizer(TextProcessor, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_entity_type(self, entity):
        pass


class SpacyNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.nlp = spacy.load("en_core_web_sm")
        self.literal_types = {"PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"}

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        entities = []
        doc = self.nlp(text)

        for ent in doc.ents:
            entities.append(Entity(None, ent.start_char, ent.end_char, ent.text, e_type=ent.label_))

        return entities

    def get_entity_type(self, entity: Entity) -> EntityType:
        if entity.type in self.literal_types:
            return EntityType.LITERAL
        else:
            return EntityType.ENTITY


class StanzaNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.nlp = stanza.Pipeline(lang="en", processors="tokenize,mwt,ner")

    def get_entity_type(self, entity):
        pass

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        entities = []
        doc = self.nlp(text)

        for entity in doc.ents:
            entities.append(Entity(
                url=None,
                start_idx=entity.start_char,
                end_idx=entity.end_char,
                text=entity.text,
                label=None,
                score=None,
                e_type=entity.type
            ))

        return entities


class SparkNLPNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        logging.getLogger("py4j").setLevel(level=logging.WARN)
        self.spark = sparknlp.start(gpu=True)
        # self.spark.sparkContext.setLogLevel("WARN")
        self.nlp_onto = PretrainedPipeline("onto_recognize_entities_lg", "en")
        self.nlp_dl = PretrainedPipeline("recognize_entities_dl", "en")

    def get_entity_type(self, entity):
        pass

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        pipelines = [self.nlp_onto, self.nlp_dl]

        results = []
        for pipeline in pipelines:
            results.extend(pipeline.fullAnnotate(text))

        entities = []

        for result in results:
            for annotation in result["entities"]:
                entity = Entity(url=None,
                                start_idx=annotation.begin,
                                end_idx=annotation.end + 1,
                                text=annotation.result,
                                label=None,
                                score=None,
                                e_type=annotation.metadata.entity)

                entities.append(entity)

        return entities


class EnsembleNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.ner = [SparkNLPNER(), StanzaNER(), SpacyNER()]

    def get_entity_type(self, entity):
        pass

    def process(self, text: str) -> List[Entity]:
        entities = set()

        for ner in self.ner:
            entities = entities.union(ner.process(text))

        return list(entities)


if __name__ == '__main__':
    ner = SparkNLPNER()
    print(ner.process("The Bauhaus-Universität Weimar is a university located in Weimar, Germany."))
