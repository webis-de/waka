import abc
import copy
import os
import sys
from typing import List

from elasticsearch import Elasticsearch, AuthenticationException

from waka.nlp.kg import Triple
from waka.nlp.text_processor import TextProcessor


class RelationLinker(TextProcessor[List[Triple], List[Triple]], metaclass=abc.ABCMeta):
    pass


class ElasticRelationLinker(RelationLinker):
    def __init__(self, alpha=2, beta=0.72, min_score=8.0, max_results=33):
        super().__init__()
        self.index_name = "corpus_wikidata_properties_20240717"

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

    def process(self, text: str, triples: List[Triple]) -> List[Triple]:
        searches = []
        for triple in triples:
            searches.append({"index": self.index_name})
            query = copy.deepcopy(self.search_template)
            query["query"]["function_score"]["query"]["query_string"]["query"] = (
                triple.predicate.text
            )
            searches.append(query)

        results = self.es_client.msearch(searches=searches)
        for response, triple in zip(results["responses"], triples):
            if response["status"] != 200:
                continue

            if len(response["hits"]["hits"]) > 0:
                hit = response["hits"]["hits"][0]
                triple.predicate.url = hit["_id"]
                triple.predicate.label = hit["_source"]["label"]
                triple.predicate.description = hit["_source"]["description"]

        return triples



