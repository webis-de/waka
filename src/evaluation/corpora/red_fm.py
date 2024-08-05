import fileinput
import json
import os

from evaluation.corpora.corpus_parser import CorpusParser
from waka.nlp.kg import KnowledgeGraph, Property, Triple, LinkedEntity


class RedFM(CorpusParser):
    def __init__(self, train=False, test=True, dev=False):
        super().__init__("/mnt/ssd2/corpora/corpora-thirdparty/corpus-redfm", train=train, test=test, dev=dev)

        files = []

        if self.dev:
            files.append(os.path.join(self.data_dir, "dev.en.jsonl"))
        if self.test:
            files.append(os.path.join(self.data_dir, "test.en.jsonl"))
        if self.train:
            files.append(os.path.join(self.data_dir, "train.en.jsonl"))

        self.in_file = fileinput.FileInput(files, openhook=fileinput.hook_encoded("utf-8"))
        self.line = None

    def has_next(self) -> bool:
        self.line = self.in_file.readline()

        return self.line != ""

    def next(self) -> KnowledgeGraph:
        data = json.loads(self.line)

        text = data["text"].encode("utf-8").decode()

        entities = []
        triples = []

        # for entity in data["entities"]:
        #     entities.append(LinkedEntity(
        #             text=entity["surfaceform"].encode("utf-8").decode(),
        #             url=f"http://www.wikidata.org/entity/{entity['uri']}",
        #             start_idx=entity["boundaries"][0],
        #             end_idx=entity["boundaries"][1],
        #             label=None,
        #             e_type=entity["type"].lower(),
        #             score=None,
        #             description=None
        #         ))

        for relation in data["relations"]:
            subject = relation["subject"]
            subject_entity = LinkedEntity(
                    text=subject["surfaceform"].encode("utf-8").decode(),
                    url=f"http://www.wikidata.org/entity/{subject['uri']}",
                    start_idx=subject["boundaries"][0],
                    end_idx=subject["boundaries"][1],
                    label=None,
                    e_type=subject["type"].lower(),
                    score=None,
                    description=None
                )

            predicate = Property(
                text=relation["predicate"]["surfaceform"],
                url=f"http://www.wikidata.org/prop/direct/{relation['predicate']['uri']}",
                label=None,
                description=None
            )

            object = relation["object"]
            object_entity = LinkedEntity(
                text=object["surfaceform"].encode("utf-8").decode(),
                url=f"http://www.wikidata.org/entity/{object['uri']}",
                start_idx=object["boundaries"][0],
                end_idx=object["boundaries"][1],
                label=None,
                e_type=object["type"].lower(),
                score=None,
                description=None
            )

            entities.append(subject_entity)
            entities.append(object_entity)

            triples.append(Triple(subject_entity, predicate, object_entity, None))

        kg = KnowledgeGraph(text=text, triples=triples, entities=[], entity_mentions=list(set(entities)))

        return kg

