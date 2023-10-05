import abc
from typing import List

import numpy as np
from numpy import ndarray, dtype
from sentence_transformers.SentenceTransformer import SentenceTransformer
from sentence_transformers.util import cos_sim
from transformers import pipeline

from waka.nlp.kg import Triple, Entity, LinkedEntity


class TripleScorer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def score(self, text: str, triples: List[Triple]) -> List[Triple]:
        pass


class SentenceBert(TripleScorer):
    def __init__(self):
        self.sentence_transformer = SentenceTransformer("paraphrase-mpnet-base-v2", device="cuda")

    def _score(self, *texts: str) -> ndarray[float, dtype[float]]:
        embeddings = self.sentence_transformer.encode(texts,
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


class EntityScorer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def score(self, text: str, entities: List[Entity | LinkedEntity]) -> List[Entity | LinkedEntity]:
        pass


class BartMNLI(EntityScorer):
    def __init__(self):
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device="cuda")

    def score(self, text: str, entities: List[Entity | LinkedEntity]) -> List[Entity | LinkedEntity]:
        labels = [e.label for e in entities if isinstance(e, LinkedEntity)]

        if len(labels) > 0:
            result = self.classifier(text, labels)

            for entity, score in zip(entities, result["scores"]):
                entity.score *= score

        return entities


def main():
    scorer = SentenceBert()
    print(scorer.score(
        "St Magnus-the-Martyr, City of London is church in City of London, UK",
        "diocese is administrative division of the church to which the element belongs; use P5607 for other types of ecclesiastical territorial entities",
        "Diocese of London is forms part of the Church of England's Province of Canterbury in England"))


if __name__ == '__main__':
    main()
