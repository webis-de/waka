from __future__ import annotations

import abc
from typing import Optional, List, Any

from databind.json import dumps
from pydantic.dataclasses import dataclass


class GenericItem(metaclass=abc.ABCMeta):
    text: Optional[str]

    def __init__(self, text: Optional[str] = None):
        self.text = text

    def to_json(self) -> str:
        return dumps(self, self.__class__)

    def __str__(self):
        return self.to_json()


@dataclass
class Resource(GenericItem):
    url: Optional[str]
    start_idx: Optional[int]
    end_idx: Optional[int]
    text: Optional[str]

    def __init__(self,
                 url: Optional[str] = None,
                 start_idx: Optional[int] = None,
                 end_idx: Optional[int] = None,
                 text: Optional[str] = None,
                 ):
        super().__init__(text)
        self.url = url
        self.start_idx = start_idx
        self.end_idx = end_idx


@dataclass
class Entity(Resource):
    label: Optional[str] = None
    start_idx: Optional[int]
    end_idx: Optional[int]
    type: Optional[str] = None
    score: Optional[float] = None

    def __init__(self,
                 url: Optional[str] = None,
                 start_idx: Optional[int] = None, end_idx: Optional[int] = None,
                 text: Optional[str] = None, label: Optional[str] = None, score: Optional[float] = None,
                 e_type: Optional[str] = None):
        super().__init__(url, start_idx, end_idx, text)
        self.label = label
        self.type = e_type
        self.score = score

    def __repr__(self):
        return f"{self.start_idx}:{self.end_idx}:{self.text}"

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def from_resource(resource: Resource) -> Entity:
        return Entity(url=resource.url, start_idx=resource.start_idx, end_idx=resource.end_idx,
                      text=resource.text)


@dataclass
class Property(GenericItem):
    url: Optional[str]
    text: Optional[str]

    def __init__(self, url: Optional[str] = None, text: Optional[str] = None):
        super().__init__(text)
        self.url = url


@dataclass
class Triple:
    subject: Optional[Resource]
    predicate: Optional[Property]
    object: Optional[Resource]

    def __init__(self, subject: Optional[Resource] = None, predicate: Optional[Property] = None,
                 object: Optional[Resource] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.subject = subject
        self.predicate: Optional[Property] = predicate
        self.object: Optional[Resource] = object

    def to_json(self) -> str:
        return dumps(self, Triple)

    def __str__(self) -> str:
        return self.to_json()


@dataclass
class KnowledgeGraph:
    text: Optional[str]
    triples: List[Triple]
    entities: List[Entity]
    entity_candidates: List[Entity]

    def __str__(self) -> str:
        return self.to_rdf()

    def to_json(self) -> str:
        return dumps(self, KnowledgeGraph)

    def to_rdf(self) -> str:
        out = ""
        for triple in self.triples:
            out += f"<{triple.subject.url}> <{triple.predicate.url}> <{triple.object.url}> .\n"
        return out

    class Builder:
        triples: List[Triple]
        entities: List[Entity]

        def __init__(self,
                     text: str,
                     triples: Optional[List[Triple]] = None,
                     entities: Optional[List[Entity]] = None):
            self.text = text

            if triples is not None:
                self.triples = triples
            else:
                self.triples = []

            if entities is not None:
                self.entities = entities
            else:
                self.entities = []

            self.kg = None

        def add_triple(self, triple: Triple) -> KnowledgeGraph.Builder:
            self.triples.append(triple)
            return self

        def add_entity(self, entity: Entity) -> KnowledgeGraph.Builder:
            self.entities.append(entity)
            return self

        def build(self) -> KnowledgeGraph:
            entities_by_mention = {}
            self.kg = KnowledgeGraph(text=self.text, triples=[], entities=[], entity_candidates=[])

            for entity in self.entities:
                if entity.text not in entities_by_mention:
                    entities_by_mention[entity.text] = []

                entities_by_mention[entity.text].append(entity)

            for mention, entity in entities_by_mention.items():
                entities_by_mention[mention] = sorted(entities_by_mention[mention], key=lambda e: -e.score)
                self.kg.entity_candidates.append(entities_by_mention[mention][0])

            for triple in self.triples:
                entity = self._get_entity_for_mention(triple.subject.text, entities_by_mention)

                if entity is not None:
                    triple.subject = entity

                entity = self._get_entity_for_mention(triple.object.text, entities_by_mention)

                if entity is not None:
                    triple.object = entity

            self.kg.triples.extend(self.triples)
            self.kg.entities = list(set(self.kg.entities))

            return self.kg

        def _get_entity_for_mention(self, mention: str, entities_by_mention: dict) -> Entity:
            if mention in entities_by_mention:
                entity = entities_by_mention[mention][0]

                for i in range(1, len(entities_by_mention[mention])):
                    if entities_by_mention[mention][i].url != entity.url:
                        break

                    self.kg.entities.append(entities_by_mention[mention][i])

                self.kg.entities.append(entity)
                if entity in self.kg.entity_candidates:
                    self.kg.entity_candidates.remove(entity)

                return entity
            else:
                for mention_key in entities_by_mention:
                    if mention in mention_key:
                        entity = entities_by_mention[mention][0]
                        for i in range(1, len(entities_by_mention[mention])):
                            if entities_by_mention[mention][i].url != entity.url:
                                break

                            self.kg.entities.append(entities_by_mention[mention][i])

                        self.kg.entities.append(entity)
                        if entity in self.kg.entity_candidates:
                            self.kg.entity_candidates.remove(entity)
                        return entity

            return None