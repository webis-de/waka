import abc
from typing import Optional, List

import requests

from waka.nlp.entity_recognition import SpacyNER, EntityType
from waka.nlp.kg import Entity, Triple
from waka.nlp.text_processor import TextProcessor


class EntityLinker(TextProcessor, metaclass=abc.ABCMeta):
    pass


class ElasticEntityLinker(EntityLinker):
    def __init__(self):
        self.entity_recognizer = SpacyNER()

        self.search_endpoint = "https://metareal-kb.web.webis.de/api/v1/kb/entity/search"

    def process(self, text: str) -> Optional[List[Entity | Triple]]:
        cache = {}
        linked_entities = []

        entities = self.entity_recognizer.process(text)
        headers = {"accept": "application/json"}

        for entity in entities:
            retrieved_entities = []

            if self.entity_recognizer.get_entity_type(entity) == EntityType.LITERAL:
                continue

            if entity.text in cache:
                retrieved_entities.extend(cache[entity.text])
            else:
                request_params = {"q": entity.text}

                response = requests.get(self.search_endpoint, params=request_params, headers=headers)
                body = response.json()

                if body["status"] == "success":
                    for e in body["data"]:
                        retrieved_entities.append(e)

                    cache[entity.text] = retrieved_entities

                for e in retrieved_entities:
                    linked_entities.append(Entity(
                        e["id"],
                        entity.start_idx,
                        entity.end_idx,
                        entity.text,
                        e["label"],
                        e["score"],
                        entity.type))

        return linked_entities
