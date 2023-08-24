import abc
from threading import Thread
from typing import List

import requests

from waka.nlp.kg import Entity
from waka.nlp.text_processor import TextProcessor


class EntityLinker(TextProcessor[List[Entity], List[Entity]], metaclass=abc.ABCMeta):
    pass


class ElasticEntityLinker(EntityLinker):
    def __init__(self):
        super().__init__()
        self.search_endpoint = "https://metareal-kb.web.webis.de/api/v1/kb/entity/search"

    def process(self, in_data: List[Entity]) -> List[Entity]:
        super().process(in_data)
        # cache = {}
        linked_entities = []
        request_threads = []

        for entity in in_data:

            # if entity.text in cache:
            #     retrieved_entities.extend(cache[entity.text])
            # else:

            request = self.RequestThread(self.search_endpoint, entity)
            request.start()
            request_threads.append(request)

        for thread in request_threads:
            thread.join()

            linked_entities.extend(thread.linked_entities)

        return linked_entities

    class RequestThread(Thread):
        def __init__(self, endpoint, entity):
            super().__init__()

            self.linked_entities = []
            self.endpoint = endpoint
            self.entity = entity

        def run(self) -> None:
            retrieved_entities = []
            request_params = {"q": self.entity.text}

            response = requests.get(self.endpoint, params=request_params, headers={"accept": "application/json"})
            body = response.json()

            if body["status"] == "success":
                for e in body["data"]:
                    retrieved_entities.append(e)

            for e in retrieved_entities:
                self.linked_entities.append(Entity(
                    url=e["id"],
                    start_idx=self.entity.start_idx,
                    end_idx=self.entity.end_idx,
                    text=self.entity.text,
                    label=e["label"],
                    score=e["score"],
                    e_type=self.entity.type))

