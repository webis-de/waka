import abc
import logging
from typing import List
from enum import Enum
import spacy

from waka.nlp.text_processor import TextProcessor
from waka.nlp.kg import Entity


class EntityType(Enum):
    ENTITY = 1
    LITERAL = 2


class EntityRecognizer(TextProcessor, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_entity_type(self, entity):
        pass


class SpacyNER(EntityRecognizer):

    def __init__(self):
        logging.info("Loading SpacyNER...")
        self.nlp = spacy.load("en_core_web_sm")
        self.literal_types = {"PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"}

    def process(self, text: str) -> List[Entity]:
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


