import abc
import datetime
import logging
import os
import re
from enum import Enum
from typing import List, Optional

import dateutil.parser
import number_parser
import spacy
import sparknlp
import stanza
from flair.data import Sentence
from flair.models import SequenceTagger
from sparknlp.pretrained import PretrainedPipeline

from waka.nlp.kg import Entity
from waka.nlp.text_processor import TextProcessor


class EntityType(Enum):
    ENTITY = 1
    LITERAL = 2


class RDFType:
    DECIMAL = "http://www.w3.org/2001/XMLSchema#decimal"
    DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"


class EntityRecognizer(TextProcessor, metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()
        self.decimal_types = {"PERCENT", "MONEY", "QUANTITY", "CARDINAL", "ORDINAL"}
        self.date_types = {"DATE", "TIME"}

    def parse_decimal(self, text: str) -> Optional[str]:
        decimal = None
        try:
            decimal = float(re.sub("[^0-9.\-–]", "", text))
        except ValueError:
            pass

        if decimal is None:
            decimal = number_parser.parse_number(text)

        if decimal is None:
            decimal = number_parser.parse_ordinal(text)

        if decimal is not None:
            url = f"{decimal:+0.0f}^^{RDFType.DECIMAL}"
            return url
        else:
            self.logger.warning(f"Can't parse \"{text}\" as decimal!")

        return None

    def parse_datetime(self, text: str) -> Optional[str]:
        try:
            date = dateutil.parser.parse(text, default=datetime.datetime(1, 1, 1))
            url = f"{date.strftime('%Y-%m-%dT%H:%M:%SZ')}^^{RDFType.DATETIME}"
            return url
        except ValueError:
            self.logger.warning(f"Can't parse \"{text}\" as datetime!")

        return None


class SpacyNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.nlp = spacy.load("en_core_web_sm")

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        entities = []
        doc = self.nlp(text)

        self._add_nouns(text, doc, entities)
        self._add_noun_phrases(doc, entities)

        for entity in doc.ents:
            url = None
            if entity.label_ in self.decimal_types:
                url = self.parse_decimal(entity.text)
            elif entity.label_ in self.date_types:
                url = self.parse_datetime(entity.text)

            entities.append(Entity(
                url=url,
                start_idx=entity.start_char,
                end_idx=entity.end_char,
                text=entity.text,
                e_type=entity.label_,
            ))

        return entities

    @staticmethod
    def _add_nouns(text, doc, entities):
        last_token = None
        start_idx = None
        end_idx = None
        tags = {"PROPN", "NOUN"}

        for token in doc:
            if token.pos_ in tags:
                if last_token == token.pos_:
                    end_idx = token.idx + len(token.lemma_)

                    entities.append(Entity(
                        url=None,
                        start_idx=start_idx,
                        end_idx=end_idx,
                        text=text[start_idx:end_idx],
                        e_type=token.pos_,
                    ))
                elif start_idx is not None and end_idx is not None:
                    entities.append(Entity(
                        url=None,
                        start_idx=start_idx,
                        end_idx=end_idx,
                        text=text[start_idx:end_idx],
                        e_type=last_token,
                    ))
                    start_idx = None
                    end_idx = None

                if start_idx is None:
                    start_idx = token.idx

                if end_idx is None:
                    end_idx = token.idx + len(token.lemma_)

                entities.append(Entity(
                    url=None,
                    start_idx=token.idx,
                    end_idx=token.idx + len(token.lemma_),
                    text=text[token.idx:token.idx + len(token.lemma_)],
                    e_type=token.pos_,
                ))

            else:
                if (last_token in tags
                        and start_idx is not None
                        and end_idx is not None):
                    entities.append(Entity(
                        url=None,
                        start_idx=start_idx,
                        end_idx=end_idx,
                        text=text[start_idx:end_idx],
                        e_type=last_token,
                    ))

                    start_idx = None
                    end_idx = None

            last_token = token.pos_

        if (last_token in tags
                and start_idx is not None
                and end_idx is not None):
            entities.append(Entity(
                url=None,
                start_idx=start_idx,
                end_idx=end_idx,
                text=text[start_idx:end_idx],
                e_type=last_token
            ))

    @staticmethod
    def _add_noun_phrases(doc, entities):
        for chunk in doc.noun_chunks:
            entities.append(Entity(
                url=None,
                start_idx=chunk.start_char,
                end_idx=chunk.end_char,
                text=chunk.text,
                e_type="NOUN-PHRASE"
            ))


class StanzaNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.nlp = stanza.Pipeline(lang="en", processors="tokenize,mwt,ner")
        self.decimal_types = {"PERCENT", "MONEY", "QUANTITY", "CARDINAL", "ORDINAL"}
        self.date_types = {"DATE", "TIME"}

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        entities = []
        doc = self.nlp(text)

        for entity in doc.ents:
            url = None
            if entity.type in self.decimal_types:
                url = self.parse_decimal(entity.text)
            elif entity.type in self.date_types:
                url = self.parse_datetime(entity.text)

            entities.append(Entity(
                url=url,
                start_idx=entity.start_char,
                end_idx=entity.end_char,
                text=entity.text,
                e_type=entity.type,
            ))

        return entities


class SparkNLPNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        logging.getLogger("py4j").setLevel(level=logging.WARN)
        self.spark = sparknlp.start(gpu=True)
        # self.spark.sparkContext.setLogLevel("WARN")
        self.nlp_onto = PretrainedPipeline("onto_recognize_entities_lg", "en")
        self.nlp_dl = PretrainedPipeline("recognize_entities_dl", "en")

        self.decimal_types = {"PERCENT", "MONEY", "QUANTITY", "CARDINAL", "ORDINAL"}
        self.date_types = {"DATE", "TIME"}

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        pipelines = [self.nlp_onto, self.nlp_dl]

        results = []
        for pipeline in pipelines:
            results.extend(pipeline.fullAnnotate(text))

        entities = []

        for result in results:
            for annotation in result["entities"]:
                entity_type = annotation.metadata.getOrDefault("entity", None)
                url = None
                if entity_type in self.decimal_types:
                    url = self.parse_decimal(annotation.result)
                elif entity_type in self.date_types:
                    url = self.parse_datetime(annotation.result)

                entities.append(Entity(
                    url=url,
                    start_idx=annotation.begin,
                    end_idx=annotation.end + 1,
                    text=annotation.result,
                    e_type=entity_type))

        return entities


class FlairNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.tagger = SequenceTagger.load("flair/ner-english")

    def process(self, text: str) -> List[Entity]:
        super().process(text)
        entities = []

        sentence = Sentence(text)
        self.tagger.predict(sentence)

        for entity in sentence.get_spans("ner"):
            entities.append(Entity(
                url=None,
                start_idx=entity.start_position,
                end_idx=entity.end_position,
                text=entity.text,
                e_type=entity.get_label().value
            ))

        return entities


class EnsembleNER(EntityRecognizer):

    def __init__(self):
        super().__init__()
        self.ner = [SparkNLPNER(), StanzaNER(), SpacyNER(), FlairNER()]

    def process(self, text: str) -> List[Entity]:
        entities = set()

        for ner in self.ner:
            entities = entities.union(ner.process(text))

        # for entity in entities:
        #     new_text = re.sub("^[^a-zA-Z0-9]+", "", entity.text)
        #
        #     diff = len(entity.text) - len(new_text)
        #     entity.text = new_text
        #     entity.start_idx += diff
        #
        #     new_text = re.sub("[^a-zA-Z0-9]+$", "", entity.text)
        #
        #     diff = len(entity.text) - len(new_text)
        #     entity.text = new_text
        #     entity.end_idx -= diff

        return list(entities)


if __name__ == '__main__':
    ner = SpacyNER()
    print(ner.process(
        "The La Paz 25 is an American trailerable sailboat that was designed by Lyle C. Hess as a motorsailer and first built in 1973."))
