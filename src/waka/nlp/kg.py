from __future__ import annotations

import abc
from typing import Optional, List

from databind.json import dumps
from pydantic.dataclasses import dataclass


@dataclass(kw_only=True)
class GenericItem(metaclass=abc.ABCMeta):
    text: Optional[str]

    def to_json(self) -> str:
        return dumps(self, self.__class__)

    def __str__(self):
        return self.to_json()


@dataclass(kw_only=True)
class Resource(GenericItem):
    url: Optional[str]
    start_idx: Optional[int]
    end_idx: Optional[int]


@dataclass(kw_only=True)
class Entity(Resource):
    start_idx: Optional[int]
    end_idx: Optional[int]
    e_type: Optional[str]

    def __hash__(self):
        return hash(f"{self.start_idx}:{self.end_idx}")

    def __eq__(self, other):
        if isinstance(other, LinkedEntity):
            return self.__hash__() == Entity.__hash__(other)
        elif isinstance(other, Entity):
            return self.__hash__() == other.__hash__()

        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def from_resource(resource: Resource) -> Entity:
        return Entity(url=resource.url, start_idx=resource.start_idx, end_idx=resource.end_idx,
                      text=resource.text, e_type=None)

    @staticmethod
    def eval(desired: List[Entity], computed: List[Entity]) -> dict:
        tp = 0
        fp = 0
        for comp_entity in computed:
            if comp_entity in desired:
                tp += 1
            else:
                fp += 1

        fn = 0

        for des_entity in desired:
            if des_entity not in computed:
                fn += 1
                # print(f"{des_entity.to_json()} not in")
                # for e in sorted(computed, key=lambda x: x.start_idx):
                #     print(e.to_json())
                # print("".join(["-"]*100))

        try:
            prec = tp / (tp + fp)
        except ZeroDivisionError:
            prec = 0.0

        try:
            recall = tp / (tp + fn)
        except ZeroDivisionError:
            recall = 0.0

        try:
            f1 = 2.0 * prec * recall / (prec + recall)
        except ZeroDivisionError:
            f1 = 0.0

        return {"precision": prec, "recall": recall, "f1": f1}


@dataclass(kw_only=True)
class LinkedEntity(Entity):
    label: Optional[str]
    score: Optional[float]
    description: Optional[str]

    def __hash__(self):
        return hash(f"{self.start_idx}:{self.end_idx}:{self.url}")

    def __eq__(self, other):
        if isinstance(other, LinkedEntity):
            return self.__hash__() == other.__hash__()
        elif isinstance(other, Entity):
            return Entity.__hash__(self) == other.__hash__()

        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def from_resource(resource: Resource) -> Entity:
        return LinkedEntity(url=resource.url, start_idx=resource.start_idx, end_idx=resource.end_idx,
                            text=resource.text, label=None, e_type=None, score=None, description=None)


@dataclass(kw_only=True)
class Property(GenericItem):
    url: Optional[str]
    text: Optional[str]

    def __hash__(self):
        return hash(f"{self.text}:{self.url}")

    def __eq__(self, other):
        if isinstance(other, Property):
            return self.__hash__() == other.__hash__()

        return False

    @staticmethod
    def eval(desired_triples: List[Triple], computed_triples: List[Triple]):
        desired_predicates = [t.predicate for t in desired_triples]
        comp_predicates = [t.predicate for t in computed_triples]

        tp = 0
        fp = 0
        for comp_triple in computed_triples:
            correct = False
            if comp_triple.predicate in desired_predicates:
                for desired_triple in desired_triples:
                    if desired_triple.predicate == comp_triple.predicate:
                        if comp_triple.subject.text == desired_triple.subject.text and \
                                comp_triple.object.text == desired_triple.object.text:
                            tp += 1
                            correct = True
                            break

            if not correct:
                fp += 1

        fn = 0

        for desired_triple in desired_triples:
            if desired_triple.predicate not in comp_predicates:
                fn += 1
            else:
                for comp_triple in computed_triples:
                    if comp_triple.predicate == desired_triple.predicate:
                        if comp_triple.subject.text != desired_triple.subject.text or \
                                comp_triple.object.text != desired_triple.object.text:
                            fn += 1

        try:
            prec = tp / (tp + fp)
        except ZeroDivisionError:
            prec = 0.0

        try:
            recall = tp / (tp + fn)
        except ZeroDivisionError:
            recall = 0.0

        try:
            f1 = 2.0 * prec * recall / (prec + recall)
        except ZeroDivisionError:
            f1 = 0.0

        return {"precision": prec, "recall": recall, "f1": f1}


@dataclass
class Triple:
    subject: Optional[Resource]
    predicate: Optional[Property]
    object: Optional[Resource]

    def to_json(self) -> str:
        return dumps(self, Triple)

    def __str__(self) -> str:
        return self.to_json()

    def __eq__(self, other):
        if not isinstance(other, Triple):
            return False

        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash(f"{self.subject.url}:{self.predicate.url}:{self.object.url}")


@dataclass
class KnowledgeGraph:
    text: Optional[str]
    triples: List[Triple]
    entities: List[LinkedEntity | Entity]
    entity_candidates: List[LinkedEntity | Entity]

    def __str__(self) -> str:
        return self.to_rdf()

    def to_json(self) -> str:
        return dumps(self, KnowledgeGraph)

    def to_rdf(self) -> str:
        out = ""
        for triple in self.triples:
            out += f"<{triple.subject.url}> <{triple.predicate.url}> <{triple.object.url}> .\n"
        return out

    @staticmethod
    def eval(desired_triples: List[Triple], computed_triples: List[Triple]) -> dict:
        tp = 0
        fp = 0
        for comp_triple in computed_triples:
            if comp_triple in desired_triples:
                tp += 1
            else:
                fp += 1

        fn = 0

        for des_triple in desired_triples:
            if des_triple not in computed_triples:
                fn += 1

        try:
            prec = tp / (tp + fp)
        except ZeroDivisionError:
            prec = 0.0

        try:
            recall = tp / (tp + fn)
        except ZeroDivisionError:
            recall = 0.0

        try:
            f1 = 2.0 * prec * recall / (prec + recall)
        except ZeroDivisionError:
            f1 = 0.0

        return {"precision": prec, "recall": recall, "f1": f1}

    class Builder:
        triples: List[Triple]
        entities: List[LinkedEntity | Entity]
        kg: Optional[KnowledgeGraph]

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

                if triple.subject.url is not None and triple.object.url is not None:
                    self.kg.triples.append(triple)

            self.kg.entities = list(set(self.kg.entities))
            self.kg.triples = list(set(self.kg.triples))

            return self.kg

        def _get_entity_for_mention(self, mention: str, entities_by_mention: dict) -> Optional[LinkedEntity | Entity]:
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
                        entity = entities_by_mention[mention_key][0]
                        for i in range(1, len(entities_by_mention[mention_key])):
                            if entities_by_mention[mention_key][i].url != entity.url:
                                break

                            self.kg.entities.append(entities_by_mention[mention_key][i])

                        self.kg.entities.append(entity)
                        if entity in self.kg.entity_candidates:
                            self.kg.entity_candidates.remove(entity)
                        return entity

            return None
