import abc
import copy
import csv
import os
import re
import sys
from typing import List

from elasticsearch import Elasticsearch, AuthenticationException

from waka.nlp.kg import EntityMention, LinkedEntity
from waka.nlp.text_processor import TextProcessor


class EntityLinker(TextProcessor[List[EntityMention], List[LinkedEntity]], metaclass=abc.ABCMeta):
    pass


class ElasticEntityLinker(EntityLinker):
    def __init__(self, alpha=2, beta=1.6, min_score=8.0, max_results=40):
        super().__init__()
        self.index_name = "corpus_wikidata_20240717"

        api_key = os.getenv("ES_API_KEY")
        if api_key is None or api_key == "":
            self.logger.error("Elasticsearch API key (ES_API_KEY) not set!")
            sys.exit(1)

        try:
            self.es_client = Elasticsearch("https://elasticsearch.srv.webis.de", api_key=api_key,
                                           retry_on_timeout=True, max_retries=10)
        except AuthenticationException:
            self.logger.error("Authentication to Elasticsearch failed!")
            sys.exit(1)

        self.search_template = {
            "query": {
                "function_score": {
                    "query": {
                        "query_string": {
                            "query": None,
                            "default_operator": "AND",
                            "fields": [f"label^{alpha}", "search_key"],
                            "type": "best_fields"
                        }
                    },
                    "field_value_factor": {
                        "field": "frequency",
                        "factor": beta,
                        "missing": 1.0,
                        "modifier": "log1p"
                    }
                }
            },
            "from": 0,
            "size": max_results,
            "min_score": min_score
        }

        self.country_dict = {}

        with open("data/countries.csv", "r") as in_file:
            in_file.readline()
            reader = csv.reader(in_file)

            for row in reader:
                nationalities = row[3]
                country = row[1]

                for nationality in nationalities.split(","):
                    if nationality not in self.country_dict:
                        self.country_dict[nationality] = [country]
                    else:
                        self.country_dict[nationality].append(country)

    def process(self, text: str, in_data: List[EntityMention]) -> List[LinkedEntity]:
        super().process(text, in_data)
        linked_entities = []
        searched_entities = []
        searches = []

        for entity in in_data:
            if entity.url is not None:
                linked_entities.append(LinkedEntity(
                    text=entity.text,
                    url=entity.url,
                    start_idx=entity.start_idx,
                    end_idx=entity.end_idx,
                    e_type=entity.e_type,
                    label=None,
                    score=1.0,
                    description=None
                ))
            else:
                searched_entities.append(entity)
                searches.append({"index": self.index_name})
                search = copy.deepcopy(self.search_template)
                search["query"]["function_score"]["query"]["query_string"]["query"] = (
                    self.get_query(entity))
                searches.append(search)

        results = self.es_client.msearch(searches=searches)

        for response, entity in zip(results["responses"], searched_entities):
            if response["status"] != 200:
                continue

            for hit in response["hits"]["hits"]:
                if "label" not in hit["_source"]:
                    continue

                try:
                    if hit["_source"]["label"].lower().startswith('category:'):
                        continue
                except AttributeError:
                    pass

                if "description" not in hit["_source"]:
                    description = ""
                else:
                    description = hit["_source"]["description"]

                linked_entities.append(LinkedEntity(
                    url=hit["_id"],
                    start_idx=entity.start_idx,
                    end_idx=entity.end_idx,
                    text=entity.text,
                    label=hit["_source"]["label"],
                    score=hit["_score"] / 305,
                    e_type=entity.e_type,
                    description=description))

        return list(set(linked_entities))

    def get_query(self, entity: EntityMention):
        queries = []
        if entity.text in self.country_dict:
            queries.extend(self.country_dict[entity.text])

        queries.extend([x.strip() for x in entity.text.split(",")])
        if entity.text.replace("'s", "") != entity.text:
            queries.append(entity.text.replace("'s", ""))

        return " || ".join(map(lambda q: re.sub(
            '(\+|\-|\=|&&|\|\||\>|\<|\!|\(|\)|\{|\}|\[|\]|\^|"|~|\*|\?|\:|\\\|\/)',
            "\\\\\\1", q), queries))
