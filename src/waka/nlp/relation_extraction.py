from abc import ABCMeta
import re
from abc import ABCMeta
from enum import Enum
from typing import List, Optional

from transformers import pipeline
from openie import StanfordOpenIE
from allennlp.predictors.predictor import Predictor

from waka.nlp.kg import Triple, Resource, Property, Entity
from waka.nlp.text_processor import TextProcessor


class RelationExtractor(TextProcessor[str, Triple], metaclass=ABCMeta):
    pass


class TokenType(Enum):
    TRIPLE = 0
    SUBJECT = 1
    PREDICATE = 2
    OBJECT = 3
    NONE = 4


class RebelExtractor(RelationExtractor):

    def __init__(self):
        self.extractor = pipeline("text2text-generation",
                                  model="Babelscape/rebel-large",
                                  tokenizer='Babelscape/rebel-large')

    def process(self, text: str) -> List[Triple]:
        extraction = self.extractor(text, return_tensors=True, return_text=True)
        token_ids = extraction[0]["generated_token_ids"]
        decoded_text = self.extractor.tokenizer.batch_decode([token_ids])[0]

        return RebelExtractor.extract_triples(decoded_text, text)

    @staticmethod
    def extract_triples(tagged_text: str, original_text: str) -> List[Triple]:
        triples = []
        subject, predicate, object_ = None, None, None
        tagged_text = tagged_text.strip().replace("<s>", "") \
            .replace("<pad>", "").replace("</s>", "")

        current_type = TokenType.NONE
        substr_indices = {}

        for token in tagged_text.split():
            if token == "<triplet>":
                current_type = TokenType.TRIPLE
                if predicate is not None:
                    triples.append(Triple(subject, predicate, object_))
                    predicate = None
                subject = None
            elif token == "<subj>":
                current_type = TokenType.SUBJECT
                if predicate is not None:
                    triples.append(Triple(subject, predicate, object_))
                object_ = None
            elif token == "<obj>":
                current_type = TokenType.OBJECT
                predicate = None
            else:
                if current_type == TokenType.TRIPLE:
                    if subject is None:
                        subject = RebelExtractor.get_resource(token, original_text, substr_indices)

                    subject.text += ' ' + token
                    subject.text = subject.text.strip()
                    subject.end_idx = subject.start_idx + len(subject.text)
                elif current_type == TokenType.SUBJECT:
                    if object_ is None:
                        object_ = RebelExtractor.get_resource(token, original_text, substr_indices)

                    object_.text += ' ' + token
                    object_.text = object_.text.strip()
                    object_.end_idx = object_.start_idx + len(object_.text)
                elif current_type == TokenType.OBJECT:
                    if predicate is None:
                        predicate = Property(text="")

                    predicate.text += ' ' + token
                    predicate.text = predicate.text.strip()

        if subject is not None and predicate is not None and object_ is not None:
            triples.append(Triple(subject, predicate, object_))

        return triples

    @staticmethod
    def get_resource(token: str, original_text: str, substr_indices: dict):
        if token not in substr_indices:
            substr_indices[token] = [m.start() for m in re.finditer(f"\\b{token}\\b", original_text)]
        start_idx = substr_indices[token][0]
        substr_indices[token].pop(0)

        if len(substr_indices[token]) == 0:
            del substr_indices[token]

        return Resource(text="", start_idx=start_idx, end_idx=start_idx)


class MRebelExtractor(RelationExtractor):
    def __init__(self):
        self.extractor = pipeline('translation_xx_to_yy', model='Babelscape/mrebel-large',
                                  tokenizer='Babelscape/mrebel-large')

    def process(self, text: str) -> Optional[List[Entity | Triple]]:
        extracted_text = self.extractor.tokenizer \
            .batch_decode([self.extractor(text,
                                          decoder_start_token_id=250058,
                                          src_lang="en_XX",
                                          tgt_lang="<triplet>",
                                          return_tensors=True,
                                          return_text=False)[0]["translation_token_ids"]])

        return self.extract_triplets(extracted_text[0], text)

    @staticmethod
    def extract_triplets(tagged_text: str, original_text: str) -> List[Triple]:
        triplets = []
        tagged_text = tagged_text.strip()
        current = 'x'
        subject, relation, object_, object_type, subject_type = '', '', '', '', ''
        substr_indices = {}

        for token in tagged_text.replace("<s>", "").replace("<pad>", "").replace("</s>", "").replace("tp_XX",
                                                                                                     "").replace(
                "__en__", "").split():
            if token == "<triplet>" or token == "<relation>":
                current = 't'
                if relation != '':
                    triplets.append(Triple(
                        MRebelExtractor.get_resource(subject.strip(), original_text, substr_indices),
                        Property(None, relation.strip()),
                        MRebelExtractor.get_resource(object_.strip(), original_text, substr_indices)))
                    relation = ''
                subject = ''
            elif token.startswith("<") and token.endswith(">"):
                if current == 't' or current == 'o':
                    current = 's'
                    if relation != '':
                        triplets.append(Triple(
                            MRebelExtractor.get_resource(subject.strip(), original_text, substr_indices),
                            Property(None, relation.strip()),
                            MRebelExtractor.get_resource(object_.strip(), original_text, substr_indices)))
                    object_ = ''
                    subject_type = token[1:-1]
                else:
                    current = 'o'
                    object_type = token[1:-1]
                    relation = ''
            else:
                if current == 't':
                    subject += ' ' + token
                elif current == 's':
                    object_ += ' ' + token
                elif current == 'o':
                    relation += ' ' + token
        if subject != '' and relation != '' and object_ != '' and object_type != '' and subject_type != '':
            triplets.append(
                Triple(
                    MRebelExtractor.get_resource(subject.strip(), original_text, substr_indices),
                    Property(None, relation.strip()),
                    MRebelExtractor.get_resource(object_.strip(), original_text, substr_indices)))
        return triplets

    @staticmethod
    def get_resource(token: str, original_text: str, substr_indices: dict):
        if token not in substr_indices:
            substr_indices[token] = [m.start() for m in re.finditer(f"\\b{token}\\b", original_text)]
        start_idx = substr_indices[token][0]
        substr_indices[token].pop(0)

        if len(substr_indices[token]) == 0:
            del substr_indices[token]

        return Resource(text=token, start_idx=start_idx, end_idx=start_idx + len(token))


class OpenIEExtractor(RelationExtractor):
    def __init__(self):
        properties = {
            'openie.affinity_probability_cap': 1 / 3,
            "openie.triple.strict": True
        }

        self.client = StanfordOpenIE(properties=properties)
        self.client.annotate("dummy")
        model_url = "https://storage.googleapis.com/allennlp-public-models/coref-spanbert-large-2020.02.27.tar.gz"
        self.predictor = Predictor.from_path(model_url)

    def process(self, text: str) -> Optional[List[Triple]]:
        prediction = self.predictor.predict(document=text)

        document, clusters = prediction['document'], prediction['clusters']
        resolved_text = self.predictor.coref_resolved(text)

        triples = self.client.annotate(resolved_text)

        for triple in triples:
            print(triple)
