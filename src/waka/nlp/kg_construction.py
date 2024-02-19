from __future__ import annotations

import copy
import logging
from typing import List, Optional, Dict

import numpy as np
from Levenshtein import distance

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
        self.kg = KnowledgeGraph(text=self.text, triples=[], entities=[], entity_mentions=[])
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

                    self.kg.entities.append(best_triple.subject)
                    self.kg.entities.append(best_triple.object)
            except IndexError:
                continue

        self.kg.triples = list(set(self.kg.triples))
        self.kg.entities = list(set(self.kg.entities))
        resolved_entities = self._resolve_entity_mention_conflicts()
        self.kg.entity_mentions = []
        for entity in resolved_entities:
            self.kg.entity_mentions.extend(entity.mentions)

        return self.kg

    def _resolve_entity_mention_conflicts(self) -> List[UniqueEntity]:
        unique_entities = []
        for triple in self.kg.triples:
            unique_entities.append(triple.subject)
            unique_entities.append(triple.object)

        unique_entities = list(set(unique_entities))

        for entity in unique_entities:
            mention_copy = entity.mentions[:]
            for i in range(len(mention_copy)):
                emi = mention_copy[i]
                for j in range(i + 1, len(mention_copy)):
                    emj = mention_copy[j]

                    if emi.overlaps_with(emj):
                        dist_i = distance(emi.label, emi.text)
                        dist_j = distance(emj.label, emj.text)

                        if dist_i > dist_j:
                            entity.mentions = [e for e in entity.mentions if e is not emi]
                        else:
                            entity.mentions = [e for e in entity.mentions if e is not emj]

        conflicts = self._get_conflicts(unique_entities)

        while len(conflicts) > 0:
            conflicts = list(sorted(conflicts, key=lambda item: self._get_conflict_score(item[0], item[1])))
            entity, mention = conflicts[0]
            entity.mentions = [m for m in entity.mentions if m is not mention]

            conflicts = self._get_conflicts(unique_entities)

        # for i in range(len(unique_entities)):
        #     for em1 in unique_entities[i].mentions[:]:
        #         for j in range(i + 1, len(unique_entities)):
        #             for em2 in unique_entities[j].mentions[:]:
        #                 if em1 == em2:
        #                     continue
        #
        #                 if em1.overlaps_with(em2):
        #                     if em1.score >= em2.score and len(unique_entities[j].mentions) > 1:
        #                         unique_entities[j].mentions.remove(em2)
        #                     elif len(unique_entities[i].mentions) > 1:
        #                         unique_entities[i].mentions.remove(em1)
        #                     else:
        #                         if unique_entities[i].score >= unique_entities[j].score:
        #                             unique_entities[j].mentions.remove(em2)
        #                         else:
        #                             unique_entities[i].mentions.remove(em1)

        for triple in self.kg.triples[:]:
            if len(triple.subject.mentions) == 0 or len(triple.object.mentions) == 0:
                self.kg.triples.remove(triple)

        return unique_entities

    @staticmethod
    def _get_conflict_score(entity, mention):
        dist = distance(entity.label, mention.text)
        dist_score = 1 - (dist / max(len(entity.label), len(mention.text)))
        num_mentions = 1 / len(entity.mentions)
        length_score = len(mention.text)

        return dist_score * num_mentions * length_score * mention.score


    @staticmethod
    def _get_conflicts(unique_entities):
        conflicts = set()
        for k in range(len(unique_entities)):
            entity1 = unique_entities[k]
            for i in range(len(entity1.mentions)):
                emi = entity1.mentions[i]
                for l in range(k + 1, len(unique_entities)):
                    entity2 = unique_entities[l]
                    for j in range(len(entity2.mentions)):
                        if k == l:
                            if i == j:
                                continue

                        emj = entity2.mentions[j]
                        if emi.overlaps_with(emj):
                            conflicts.add((entity1, emi))
                            conflicts.add((entity2, emj))

        return list(conflicts)

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
