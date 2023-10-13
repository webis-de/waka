import abc
from typing import List

import requests

from waka.nlp.kg import Triple
from waka.nlp.text_processor import TextProcessor


class RelationLinker(TextProcessor[List[Triple], List[Triple]], metaclass=abc.ABCMeta):
    pass


class ElasticRelationLinker(RelationLinker):

    def __init__(self):
        super().__init__()
        self.search_endpoint = "https://metareal-kb.web.webis.de/api/v1/kb/property/search"

    def process(self, text: str, triples: List[Triple]) -> List[Triple]:
        super().process(text, triples)
        cache = {}
        headers = {"accept": "application/json"}

        with requests.Session() as session:
            for triple in triples:
                retrieved_properties = []

                if triple.predicate.text in cache:
                    retrieved_properties.extend(cache[triple.predicate.text])
                else:
                    request_params = {"q": triple.predicate.text}

                    response = session.get(self.search_endpoint, params=request_params, headers=headers)
                    body = response.json()

                    if body["status"] == "success":
                        for p in body["data"]:
                            retrieved_properties.append(p)

                        cache[triple.predicate.text] = sorted(retrieved_properties, key=lambda predicate: -predicate["score"])

                if len(retrieved_properties) > 0:
                    selected = retrieved_properties[0]
                    triple.predicate.url = selected["id"]
                    triple.predicate.label = selected["label"]
                    triple.predicate.description = selected["description"]

            return triples



