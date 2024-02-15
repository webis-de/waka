from __future__ import annotations

import copy
import logging
from typing import List, Optional, Dict

import numpy as np

from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import EnsembleNER
from waka.nlp.kg import EntityMention, Triple, KnowledgeGraph, UniqueEntity
from waka.nlp.relation_extraction import MRebelExtractor
from waka.nlp.relation_linking import ElasticRelationLinker
from waka.nlp.semantics import TripleScorer, WikidataFilter, EntitySentenceBert, BartMNLI
from waka.nlp.text_processor import Pipeline


class KGFactory:
    triples: List[Triple]
    unique_entities: List[UniqueEntity]
    kg: Optional[KnowledgeGraph]

    def __init__(self,
                 text: str,
                 triples: Optional[List[Triple]] = None,
                 entities: Optional[List[UniqueEntity]] = None,
                 triple_scorer: Optional[List[TripleScorer]] = None):
        self.text = text

        if triples is not None:
            self.triples = triples
        else:
            self.triples = []

        if entities is not None:
            self.unique_entities = entities
        else:
            self.unique_entities = []

        self.kg = None

        self.triple_scorer = triple_scorer

    def add_triple(self, triple: Triple) -> KGFactory:
        self.triples.append(triple)
        return self

    def add_entity(self, entity: UniqueEntity) -> KGFactory:
        self.unique_entities.append(entity)
        return self

    def build(self) -> KnowledgeGraph:
        self.kg = KnowledgeGraph(text=self.text, triples=[], entities=[], entity_candidates=[])
        entities_by_mention = self._construct_entity_by_mention_index()

        triple_sets = []

        for triple in self.triples:
            triple_candidates = []

            sub_entities = self._get_entities_for_mention(triple.subject.text, entities_by_mention)
            obj_entities = self._get_entities_for_mention(triple.object.text, entities_by_mention)

            for subj in sub_entities:
                for obj in obj_entities:
                    if subj.url != obj.url:
                        triple_candidate = Triple(
                            subject=subj,
                            predicate=triple.predicate,
                            object=obj,
                            score=float(np.mean([subj.score, obj.score])))

                        if triple_candidate.score >= 0.1:
                            triple_candidates.append(triple_candidate)

            triple_sets.append(list(sorted(triple_candidates, key=lambda t: -t.score)))

        if self.triple_scorer is not None:
            triple_candidates = []
            for triple_set in triple_sets:
                if len(triple_set) > 10:
                    triple_set = triple_set[:10]

                triple_candidates.extend(triple_set)

            for triple_scorer in self.triple_scorer:
                triple_candidates = triple_scorer.score(self.text, triple_candidates)

        for triple_set in triple_sets:
            try:
                triple_ranking = sorted(triple_set, key=lambda t: -t.score)
                best_triple = triple_ranking[0]
                if best_triple.score >= 0.1:
                    self.kg.triples.append(best_triple)
                    if isinstance(best_triple.subject, UniqueEntity):
                        self.kg.entities.extend(best_triple.subject.mentions)
                    else:
                        self.kg.entities.append(best_triple.subject)

                    if isinstance(best_triple.object, UniqueEntity):
                        self.kg.entities.extend(best_triple.object.mentions)
                    else:
                        self.kg.entities.append(best_triple.object)
            except IndexError:
                continue

        self.kg.entities = list(self.kg.entities)
        self.kg.triples = list(set(self.kg.triples))

        return self.kg

    def _construct_entity_by_mention_index(self) -> Dict[str, List[UniqueEntity]]:
        entities_by_mention = {}

        for entity in self.unique_entities:
            for mention in entity.mentions:
                if mention.text not in entities_by_mention:
                    entities_by_mention[mention.text] = []

                if entity not in entities_by_mention[mention.text]:
                    entity_copy = copy.deepcopy(entity)
                    entity_copy.score = mention.score
                    entities_by_mention[mention.text].append(entity_copy)

        for mention, entity in entities_by_mention.items():
            entities_by_mention[mention] = sorted(entities_by_mention[mention], key=lambda e: -e.score)

        return entities_by_mention

    @staticmethod
    def _get_entities_for_mention(mention: str,
                                  entities_by_mention: Dict[str, List[UniqueEntity]]) \
            -> List[UniqueEntity]:
        entities = []

        if len(mention) == 0:
            return entities

        if mention in entities_by_mention:
            entities.extend(entities_by_mention[mention])
        else:
            for mention_key in sorted(entities_by_mention.keys(), key=lambda m: len(m), reverse=True):
                if mention in mention_key:
                    entities.extend(entities_by_mention[mention_key])
                    break

        return entities


class KGConstructor:

    def __init__(self, scorer=None):
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self.logger = logging.getLogger(KGConstructor.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.er = EnsembleNER
        self.el = ElasticEntityLinker
        self.re = MRebelExtractor
        self.rl = ElasticRelationLinker

        self.el_pipeline = Pipeline[List[EntityMention]]()

        self.el_pipeline.add_processor(self.er)
        self.el_pipeline.add_processor(self.el)
        self.el_pipeline.add_processor(EntitySentenceBert)

        self.rl_pipeline = Pipeline[List[Triple]]()
        self.rl_pipeline.add_processor(self.re)
        self.rl_pipeline.add_processor(self.rl)

        if scorer is None:
            self.triple_scorer = [
                WikidataFilter(),
                BartMNLI()
            ]
        else:
            self.triple_scorer = [x() for x in scorer]

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

        kg_factory = KGFactory(text, triples, entities, self.triple_scorer)
        kg = kg_factory.build()
        self.logger.debug(f"Constructed graph: {kg.to_json()}")

        return kg

    def __del__(self):
        self.el_pipeline.end()
        self.rl_pipeline.end()
        self.el_pipeline.join()
        self.rl_pipeline.join()
