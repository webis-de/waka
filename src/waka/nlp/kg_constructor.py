from typing import List

from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import SpacyNER
from waka.nlp.kg import Entity, Triple, KnowledgeGraph
from waka.nlp.relation_extraction import MRebelExtractor
from waka.nlp.relation_linking import ElasticRelationLinker
from waka.nlp.text_processor import Pipeline


class KnowledgeGraphConstructor:

    def __init__(self):
        self.er = SpacyNER()
        self.el = ElasticEntityLinker()
        self.re = MRebelExtractor()
        self.rl = ElasticRelationLinker()

        self.el_pipeline = Pipeline[List[Entity]]()

        self.el_pipeline.add_processor(self.er)
        self.el_pipeline.add_processor(self.el)

        self.rl_pipeline = Pipeline[List[Triple]]()
        self.rl_pipeline.add_processor(self.re)
        self.rl_pipeline.add_processor(self.rl)

    def construct(self, text: str) -> KnowledgeGraph:
        entities = self.el_pipeline.process(text)
        triples = self.rl_pipeline.process(text)

        for triple in triples:
            entities.extend(self.el.process([
                Entity.from_resource(triple.subject),
                Entity.from_resource(triple.object)]))

        kg_builder = KnowledgeGraph.Builder(text, triples, entities)
        kg = kg_builder.build()

        return kg
