from __future__ import annotations

import logging
from typing import List, Optional, Dict

import numpy as np

from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import EnsembleNER
from waka.nlp.kg import Entity, Triple, KnowledgeGraph, LinkedEntity
from waka.nlp.relation_extraction import MRebelExtractor
from waka.nlp.relation_linking import ElasticRelationLinker
from waka.nlp.semantics import TripleScorer, EntityScorer, WikidataFilter, EntitySentenceBert
from waka.nlp.text_processor import Pipeline


class KGFactory:
    triples: List[Triple]
    entities: List[LinkedEntity | Entity]
    kg: Optional[KnowledgeGraph]

    def __init__(self,
                 text: str,
                 triples: Optional[List[Triple]] = None,
                 entities: Optional[List[Entity]] = None,
                 triple_scorer: Optional[TripleScorer] = None,
                 entity_scorer: Optional[EntityScorer] = None):
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

        self.triple_scorer = triple_scorer
        self.entity_scorer = entity_scorer

    def add_triple(self, triple: Triple) -> KGFactory:
        self.triples.append(triple)
        return self

    def add_entity(self, entity: Entity) -> KGFactory:
        self.entities.append(entity)
        return self

    def build(self) -> KnowledgeGraph:
        self.kg = KnowledgeGraph(text=self.text, triples=[], entities=[], entity_candidates=[])
        entities_by_mention = self._construct_entity_by_mention_index()

        for triple in self.triples:
            triple_candidates = []

            sub_entities = self._get_entities_for_mention(triple.subject.text, entities_by_mention)
            obj_entities = self._get_entities_for_mention(triple.object.text, entities_by_mention)

            for subj in sub_entities:
                for obj in obj_entities:
                    triple_candidates.append(
                        Triple(subj, triple.predicate, obj, float(np.mean([subj.score, obj.score]))))

            if self.triple_scorer is not None:
                triple_candidates = self.triple_scorer.score(self.text, triple_candidates)

            try:
                best_triple = sorted(triple_candidates, key=lambda t: -t.score)[0]
                self.kg.triples.append(best_triple)

                self.kg.entities.extend(self._find_mentions_for_entity(best_triple.subject))
                self.kg.entities.extend(self._find_mentions_for_entity(best_triple.object))
            except IndexError:
                continue

        self.kg.entities = list(set(self.kg.entities))
        self.kg.triples = list(set(self.kg.triples))

        return self.kg

    def _construct_entity_by_mention_index(self) -> Dict[str, List[Entity | LinkedEntity]]:
        entities_by_mention = {}
        urls_by_mention = {}

        for entity in self.entities:
            if entity.text not in entities_by_mention:
                entities_by_mention[entity.text] = []
            if entity.text not in urls_by_mention:
                urls_by_mention[entity.text] = set()

            if entity.url in urls_by_mention[entity.text]:
                continue

            urls_by_mention[entity.text].add(entity.url)
            entities_by_mention[entity.text].append(entity)

        if self.entity_scorer is not None:
            for mention, entity in entities_by_mention.items():
                entities_by_mention[mention] = self.entity_scorer.score(self.text, entities_by_mention[mention])
                entities_by_mention[mention] = sorted(entities_by_mention[mention], key=lambda e: -e.score)

        return entities_by_mention

    @staticmethod
    def _get_entities_for_mention(mention: str,
                                  entities_by_mention: Dict[str, List[Entity | LinkedEntity]]) \
            -> List[Entity | LinkedEntity]:
        entities = []

        if mention in entities_by_mention:
            entities.extend(entities_by_mention[mention])
        else:
            for mention_key in entities_by_mention:
                if mention in mention_key:
                    entities.extend(entities_by_mention[mention_key])

        return entities

    def _find_mentions_for_entity(self, entity: Entity | LinkedEntity):
        return [x for x in self.entities if x.url == entity.url and x.text == entity.text]

class KGConstructor:

    def __init__(self):
        self.logger = logging.getLogger(KGConstructor.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.er = EnsembleNER
        self.el = ElasticEntityLinker
        self.re = MRebelExtractor
        self.rl = ElasticRelationLinker

        self.el_pipeline = Pipeline[List[Entity]]()

        self.el_pipeline.add_processor(self.er)
        self.el_pipeline.add_processor(self.el)
        self.el_pipeline.add_processor(EntitySentenceBert)

        self.rl_pipeline = Pipeline[List[Triple]]()
        self.rl_pipeline.add_processor(self.re)
        self.rl_pipeline.add_processor(self.rl)

        # self.triple_scorer = SentenceBert()
        self.triple_scorer = WikidataFilter()
        self.entity_scorer = None

        try:
            self.el_pipeline.start()
            self.rl_pipeline.start()
        except Exception as e:
            self.logger.error(e.with_traceback(None))

    def construct(self, text: str) -> KnowledgeGraph:
        self.logger.setLevel(logging.DEBUG)
        self.el_pipeline.process(text)
        self.rl_pipeline.process(text)

        entities = self.el_pipeline.get()
        triples = self.rl_pipeline.get()

        self.logger.debug(f"Found entities: {entities}")
        self.logger.debug(f"Found triples: {triples}")

        kg_factory = KGFactory(text, triples, entities, self.triple_scorer, self.entity_scorer)
        kg = kg_factory.build()
        self.logger.debug(f"Constructed graph: {kg.to_json()}")

        return kg

    def __del__(self):
        self.el_pipeline.end()
        self.rl_pipeline.end()
        self.el_pipeline.join()
        self.rl_pipeline.join()
