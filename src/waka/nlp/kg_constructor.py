import logging
from typing import List

from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import EnsembleNER
from waka.nlp.kg import Entity, Triple, KnowledgeGraph
from waka.nlp.relation_extraction import MRebelExtractor
from waka.nlp.relation_linking import ElasticRelationLinker
from waka.nlp.text_processor import Pipeline


class KnowledgeGraphConstructor:

    def __init__(self):
        self.logger = logging.getLogger(KnowledgeGraphConstructor.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.er = EnsembleNER
        self.el = ElasticEntityLinker
        self.re = MRebelExtractor
        self.rl = ElasticRelationLinker

        self.el_pipeline = Pipeline[List[Entity]]()

        self.el_pipeline.add_processor(self.er)
        self.el_pipeline.add_processor(self.el)

        self.rl_pipeline = Pipeline[List[Triple]]()
        self.rl_pipeline.add_processor(self.re)
        self.rl_pipeline.add_processor(self.rl)

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

        kg_builder = KnowledgeGraph.Builder(text, triples, entities)
        kg = kg_builder.build()
        self.logger.debug(f"Constructed graph: {kg.to_json()}")

        return kg

    def __del__(self):
        self.el_pipeline.end()
        self.rl_pipeline.end()
        self.el_pipeline.join()
        self.rl_pipeline.join()
