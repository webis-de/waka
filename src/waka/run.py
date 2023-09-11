import logging
import multiprocessing

from waka.nlp.kg_constructor import KnowledgeGraphConstructor


def main():
    multiprocessing.set_start_method("spawn")
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

    kg_construct = KnowledgeGraphConstructor()
    kg = kg_construct.construct(text)

    for triple in kg.triples:
        print(f"{triple.subject.label},{triple.predicate.label},{triple.object.label}")


if __name__ == '__main__':
    main()
