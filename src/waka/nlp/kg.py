from __future__ import annotations

import abc
import logging
from typing import Optional, List, Dict
from databind.core.dataclasses import dataclass
from databind.json import dumps


@dataclass
class GenericItem(metaclass=abc.ABCMeta):
    text: Optional[str]

    def __init__(self,
                 text: Optional[str] = None):
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
        self.text = text


@dataclass
class Entity(Resource):
    label: Optional[str]
    start_idx: Optional[int]
    end_idx: Optional[int]
    type: Optional[str]
    score: Optional[float] = None

    def __init__(self, url: Optional[str] = None,
                 start_idx: Optional[int] = None, end_idx: Optional[int] = None,
                 text: Optional[str] = None, label: Optional[str] = None, score: Optional[float] = None,
                 e_type: Optional[str] = None):
        super().__init__(url, start_idx, end_idx, text)
        self.label = label
        self.type = e_type
        self.score = score

    @staticmethod
    def from_resource(resource: Resource) -> Entity:
        return Entity(resource.url, resource.start_idx, resource.end_idx,
                      resource.text, None)


@dataclass
class Property(GenericItem):
    url: Optional[str]

    def __init__(self, url: Optional[str] = None, text: Optional[str] = None):
        self.url = url
        super().__init__(text)


@dataclass
class Triple:
    subject: Optional[Resource]
    predicate: Optional[Property]
    object: Optional[Resource]

    def __init__(self, subject: Optional[Resource] = None,
                 predicate: Optional[Property] = None,
                 object: Optional[Resource] = None):
        self.subject = subject
        self.predicate: Optional[Property] = predicate
        self.object: Optional[Resource] = object

    def to_json(self) -> str:
        return dumps(self, Triple)

    def __str__(self) -> str:
        return self.to_json()


@dataclass
class KnowledgeGraph:
    text: str
    triples: List[Triple]

    def __init__(self,
                 text: str,
                 triples: Optional[List[Triple]] = None):
        self.text = text

        if triples is not None:
            self.triples = triples
        else:
            self.triples = []

        self.logger = logging.getLogger(KnowledgeGraph.__name__)

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

        def add_triple(self, triple: Triple) -> KnowledgeGraph.Builder:
            self.triples.append(triple)
            return self

        def add_entity(self, entity: Entity) -> KnowledgeGraph.Builder:
            self.entities.append(entity)
            return self

        def build(self) -> KnowledgeGraph:
            entities_by_mention = {}

            for entity in self.entities:
                if entity.text not in entities_by_mention:
                    entities_by_mention[entity.text] = []

                entities_by_mention[entity.text].append(entity)

            for mention, entity in entities_by_mention.items():
                entities_by_mention[mention] = sorted(entities_by_mention[mention], key=lambda e: -e.score, )

            kg = KnowledgeGraph(self.text)
            for triple in self.triples:
                if triple.subject.text in entities_by_mention:
                    triple.subject = entities_by_mention[triple.subject.text][0]

                if triple.object.text in entities_by_mention:
                    triple.object = entities_by_mention[triple.object.text][0]

            kg.triples.extend(self.triples)

            return kg
