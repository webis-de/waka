import logging
from typing import List

from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import SpacyNER
from waka.nlp.kg import KnowledgeGraph, Entity, Triple
from waka.nlp.relation_extraction import OpenIEExtractor, MRebelExtractor
from waka.nlp.relation_linking import ElasticRelationLinker
from waka.nlp.text_processor import Pipeline


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    text = "The Bauhaus-Universität Weimar is a university located in Weimar, Germany, and specializes in the " \
           "artistic and technical fields. Established in 1860 as the Great Ducal Saxon Art School, it gained " \
           "collegiate status on 3 June 1910. In 1919 the school was renamed Bauhaus by its new director Walter " \
           "Gropius and it received its present name in 1996. There are more than 4000 students enrolled, " \
           "with the percentage of international students above the national average at around 27%. In 2010 the " \
           "Bauhaus-Universität Weimar commemorated its 150th anniversary as an art school and college in Weimar. In " \
           "2019 the university celebrated the centenary of the founding of the Bauhaus, together with partners all " \
           "over the world."

    el_pipeline = Pipeline[List[Entity]]()
    el_pipeline.add_processor(SpacyNER())
    el_pipeline.add_processor(ElasticEntityLinker())

    entities = el_pipeline.process(text)

    rl_pipeline = Pipeline[List[Triple]]()
    rl_pipeline.add_processor(MRebelExtractor())
    rl_pipeline.add_processor(ElasticRelationLinker())

    triples = rl_pipeline.process(text)

    kg_builder = KnowledgeGraph.Builder(text, triples, entities)
    kg = kg_builder.build()
    print(kg)


if __name__ == '__main__':
    main()
