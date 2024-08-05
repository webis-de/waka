import abc
from typing import List

import numpy as np
import requests
import torch
from nltk.tokenize import PunktSentenceTokenizer
from numpy import ndarray, dtype
from sentence_transformers.SentenceTransformer import SentenceTransformer
from sentence_transformers.util import cos_sim
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

from waka.nlp.kg import Triple, LinkedEntity, UniqueEntity
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

    QUERY_LITERAL_TEMPLATE = \
        "ASK FROM <https://www.wikidata.org/wiki/> {{ <{}> <{}> \"{}\" }}"

    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        return self.send_all(triples)

    def send_all(self, triples: List[Triple]) -> List[Triple]:
        results = []
        with requests.Session() as session:
            for triple in triples:
                results.append(self.send_request(session, triple))

        for result, triple in zip(results, triples):
            if result:
                triple.score *= 3

        return triples

    def send_request(self, session: requests.Session, triple: Triple) -> bool:
        if triple.object.e_type == "entity":
            query = WikidataFilter.QUERY_TEMPLATE.format(triple.subject.url, triple.predicate.url, triple.object.url)
        else:
            query = WikidataFilter.QUERY_LITERAL_TEMPLATE.format(triple.subject.url, triple.predicate.url, triple.object.url)

        response = session.post(WikidataFilter.SPARQL_ENDPOINT, data=query,
                                headers={"Content-Type": "application/sparql-query"})

        body = response.json()

        if body["status"] == "success":
            return "true" == body["data"]["results"][0][0]


class EntityScorer(TextProcessor[List[LinkedEntity], List[UniqueEntity]], metaclass=abc.ABCMeta):
    LITERAL_TYPES = {"PERCENT", "MONEY", "QUANTITY", "CARDINAL", "ORDINAL", "DATE", "TIME"}

    @abc.abstractmethod
    def score(self, text: str, entities: List[LinkedEntity]) -> List[LinkedEntity]:
        pass

    def process(self, text: str, entities: List[LinkedEntity]) -> List[UniqueEntity]:
        return self.get_unique_entities(self.score(text, entities))

    @staticmethod
    def get_unique_entities(entities: List[LinkedEntity]) -> List[UniqueEntity]:
        url_mention_cluster = {}
        mention_clusters = []

        for entity in entities:
            if entity.url not in url_mention_cluster:
                url_mention_cluster[entity.url] = set()

            url_mention_cluster[entity.url].add(entity)

        for url, cluster in url_mention_cluster.items():
            if len(cluster) > 0:
                sorted_cluster = sorted(cluster, key=lambda e: e.score, reverse=True)
                literal = all(map(lambda e: e.e_type in EntityScorer.LITERAL_TYPES, cluster))

                first = next(iter(sorted_cluster))

                if literal:
                    mention_clusters.append(UniqueEntity(
                        url=url,
                        label=first.label,
                        description=first.description,
                        score=first.score,
                        mentions=list(sorted_cluster),
                        e_type="literal"
                    ))
                else:
                    mention_clusters.append(UniqueEntity(
                        url=url,
                        label=first.label,
                        description=first.description,
                        score=first.score,
                        mentions=list(sorted_cluster),
                        e_type="entity"
                    ))

        return mention_clusters


class BartMNLI(TripleScorer):
    def __init__(self):
        super().__init__()
        self.nli_model = AutoModelForSequenceClassification.from_pretrained('models/bart-large-mnli', local_files_only=True)
        self.tokenizer = AutoTokenizer.from_pretrained('models/bart-large-mnli', local_files_only=True)
        # self.nli_model = AutoModelForSequenceClassification.from_pretrained('MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli')
        # self.tokenizer = AutoTokenizer.from_pretrained('MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli')
        self.classifier = pipeline("zero-shot-classification", model=self.nli_model, tokenizer=self.tokenizer,
                                   device=torch.cuda.current_device())

    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        labels = {}
        for t in triples:
            if t.object.label is not None:
                label = f"{t.subject.label} ({t.subject.description}) {t.predicate.label} {t.object.label} ({t.object.description})"
            else:
                label = f"{t.subject.label} ({t.subject.description}) {t.predicate.label} {t.object.url}"

            if label not in labels:
                labels[label] = []
            labels[label].append(t)

        if len(labels) > 0:
            result = self.classifier(text, list(labels.keys()),  multi_label=True)

            for label, score in zip(result["labels"], result["scores"]):
                for triple in labels[label]:
                    triple.score *= score

        return triples


class EntitySentenceBert(EntityScorer):

    def __init__(self):
        super().__init__()
        self.sentence_transformer = SentenceTransformer("models/all-distilroberta-v1", device="cuda")

    def score(self, text: str, entities: List[LinkedEntity]) -> List[LinkedEntity]:
        sentence_spans = PunktSentenceTokenizer().span_tokenize(text)
        score_entities = list(filter(lambda e:
                                     hasattr(e, "label")
                                     and (e.label is not None or e.description is not None),
                                     entities))

        score_entities = list(sorted(score_entities, key=lambda e: e.start_idx))
        entity_iter = iter(score_entities)
        entity = None
        for span in sentence_spans:
            sentence_entities = []

            while True:
                if len(sentence_entities) == 0:
                    if entity is not None and span[0] <= entity.start_idx and entity.end_idx <= span[1]:
                        sentence_entities.append(entity)

                entity = next(entity_iter, None)

                if entity is None:
                    break

                if entity.start_idx < span[0] or entity.end_idx > span[1]:
                    break

                sentence_entities.append(entity)

            texts = [f"{c.label} is a {c.description}" for c in sentence_entities]
            sentences = [text[span[0]:span[1]], *texts]
            embeddings = self.sentence_transformer.encode(sentences,
                                                          convert_to_tensor=True)

            for i in range(1, len(embeddings)):
                sim = cos_sim(embeddings[0], embeddings[i])[0][0].item()
                sentence_entities[i - 1].score *= sim

        entities = list(sorted(entities, key=lambda e: e.score, reverse=True))
        # return entities
        return list(filter(lambda e: e.score >= 0.05, entities))
