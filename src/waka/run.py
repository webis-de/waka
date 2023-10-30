import logging
import multiprocessing

from waka.nlp.kg_construction import KGConstructor


def main():
    multiprocessing.set_start_method("spawn")
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    text = "\"The Tell-Tale Heart\" is a short story by American writer Edgar Allan Poe, first published in 1843. It is related by an unnamed narrator who endeavors to convince the reader of the narrator's sanity while simultaneously describing a murder the narrator committed. The victim was an old man with a filmy pale blue \"vulture-eye\", as the narrator calls it. The narrator emphasizes the careful calculation of the murder, attempting the perfect crime, complete with dismembering the body in the bathtub and hiding it under the floorboards. Ultimately, the narrator's actions result in hearing a thumping sound, which the narrator interprets as the dead man's beating heart."

    kg_construct = KGConstructor()
    kg = kg_construct.construct(text)

    for triple in kg.triples:
        print(f"{triple.subject.label},{triple.predicate.label},{triple.object.label}")


if __name__ == '__main__':
    main()
