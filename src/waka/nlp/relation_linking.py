import abc
from typing import Optional, List

import requests

from waka.nlp.kg import Entity, Triple, Property
from waka.nlp.relation_extraction import RebelExtractor, MRebelExtractor
from waka.nlp.text_processor import TextProcessor


class RelationLinker(TextProcessor[List[Triple], List[Triple]], metaclass=abc.ABCMeta):
    pass


class ElasticRelationLinker(RelationLinker):

    def __init__(self):
        self.search_endpoint = "https://metareal-kb.web.webis.de/api/v1/kb/property/search"

    def process(self, triples: List[Triple]) -> List[Triple]:
        cache = {}
        headers = {"accept": "application/json"}

        for triple in triples:
            retrieved_properties = []

            if triple.predicate.text in cache:
                retrieved_properties.extend(cache[triple.predicate.text])
            else:
                request_params = {"q": triple.predicate.text}

                response = requests.get(self.search_endpoint, params=request_params, headers=headers)
                body = response.json()

                if body["status"] == "success":
                    for p in body["data"]:
                        retrieved_properties.append(p)

                    cache[triple.predicate.text] = sorted(retrieved_properties, key=lambda predicate: -predicate["score"])

            if len(retrieved_properties) > 0:
                selected = retrieved_properties[0]
                triple.predicate.url = selected["id"]

        return triples



