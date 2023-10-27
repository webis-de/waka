import abc
from typing import List, Optional

import numpy as np
import requests
from numpy import ndarray, dtype
from sentence_transformers.SentenceTransformer import SentenceTransformer
from sentence_transformers.util import cos_sim
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

from waka.nlp.kg import Triple, Entity, LinkedEntity
from waka.nlp.text_processor import TextProcessor


class TripleScorer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        pass


class SentenceBert(TripleScorer):
    def __init__(self):
        self.sentence_transformer = SentenceTransformer("paraphrase-mpnet-base-v2", device="cuda")

    def _score(self, *texts: str) -> ndarray[float, dtype[float]]:
        embeddings = self.sentence_transformer.encode(*texts,
                                                      convert_to_tensor=True)

        flat_sim_triples = np.zeros((len(texts) // 3, 3))
        for i in range(0, len(texts), 3):
            flat_sim_triples[i // 3][i % 3] = cos_sim(embeddings[i], embeddings[i + 1])[0][0].item()
            flat_sim_triples[i // 3][(i + 1) % 3] = cos_sim(embeddings[i + 1], embeddings[i + 2])[0][0].item()
            flat_sim_triples[i // 3][(i + 2) % 3] = cos_sim(embeddings[i], embeddings[i + 2])[0][0].item()

        return np.mean(flat_sim_triples, axis=1)

    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        texts = []

        for triple in triples:
            texts.append(f"{triple.subject.label} is {triple.subject.description}")
            texts.append(f"{triple.predicate.label} is {triple.predicate.description}")
            texts.append(f"{triple.object.label} is {triple.object.description}")

        scores = self._score(*texts)

        for i in range(len(triples)):
            triples[i].score *= float(scores[i])

        return triples


class WikidataFilter(TripleScorer):
    SPARQL_ENDPOINT = \
        "https://metareal-kb.web.webis.de/api/v1/kb/sparql?timeout=30000"
    QUERY_TEMPLATE = \
        "ASK FROM <https://www.wikidata.org/wiki/> {{ <{}> <{}> <{}> }}"

    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        return self.send_all(triples)

    def send_all(self, triples: List[Triple]) -> List[Triple]:
        results = []
        result_triples = []
        with requests.Session() as session:
            for triple in triples:
                results.append(self.send_request(session, triple))

        # results = await asyncio.gather(*results, return_exceptions=True)

        for result, triple in zip(results, triples):
            if result:
                result_triples.append(triple)

        if len(result_triples) == 0:
            return triples

        return result_triples

    def send_request(self, session: requests.Session, triple: Triple) -> bool:
        query = WikidataFilter.QUERY_TEMPLATE.format(triple.subject.url, triple.predicate.url, triple.object.url)

        response = session.post(WikidataFilter.SPARQL_ENDPOINT, data=query,
                                headers={"Content-Type": "application/sparql-query"})

        body = response.json()

        if body["status"] == "success":
            return "true" == body["data"]["results"][0][0]


class EntityScorer(TextProcessor[List[Entity | LinkedEntity], List[Entity | LinkedEntity]], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def score(self, text: str, entities: List[Entity | LinkedEntity]) -> List[Entity | LinkedEntity]:
        pass


class BartMNLI(TripleScorer):
    def __init__(self):
        super().__init__()
        self.nli_model = AutoModelForSequenceClassification.from_pretrained('facebook/bart-large-mnli')
        self.tokenizer = AutoTokenizer.from_pretrained('facebook/bart-large-mnli')
        self.classifier = pipeline("zero-shot-classification", model=self.nli_model, tokenizer=self.tokenizer, device="cuda")

    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        labels = {}
        for t in triples:
            label = f"{t.subject.label} {t.predicate.label} {t.object.label}"
            if label not in labels:
                labels[label] = []
            labels[label].append(t)

        if len(labels) > 0:
            result = self.classifier(text, list(labels.keys()))

            for label, score in zip(result["labels"], result["scores"]):
                for triple in labels[label]:
                    triple.score *= score

        return triples

class EntityBartMNLI(EntityScorer):
    def __init__(self):
        super().__init__()
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device="cuda")

    def score(self, text: str, entities: List[Entity | LinkedEntity]) -> List[Entity | LinkedEntity]:
        labels = [e.label for e in entities if isinstance(e, LinkedEntity)]

        if len(labels) > 0:
            result = self.classifier(text, labels)

            for entity, score in zip(entities, result["scores"]):
                entity.score *= score

        return entities


class EntitySentenceBert(EntityScorer):

    def __init__(self):
        super().__init__()
        self.sentence_transformer = SentenceTransformer("all-distilroberta-v1", device="cuda")

    def score(self, text: str, entities: List[Entity | LinkedEntity]) -> List[Entity | LinkedEntity]:
        texts = [f"{e.label} is a {e.description}" for e in entities]
        embeddings = self.sentence_transformer.encode([text, *texts],
                                                      convert_to_tensor=True)

        for i in range(1, len(embeddings)):
            entities[i - 1].score *= cos_sim(embeddings[0], embeddings[i])[0][0].item()

        return entities

    def process(self, text: str, in_data: List[Entity | LinkedEntity]) -> Optional[List[Entity | LinkedEntity]]:
        return self.score(text, in_data)
