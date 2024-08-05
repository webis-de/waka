import re
from abc import ABCMeta
from enum import Enum
from typing import List, Optional

from nltk.tokenize import sent_tokenize
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

from waka.nlp.kg import Triple, Property, EntityMention
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
        super().__init__()
        self.extractor = pipeline("text2text-generation",
                                  model="Babelscape/rebel-large",
                                  tokenizer='Babelscape/rebel-large')

    def process(self, text: str, in_data: str) -> List[Triple]:
        super().process(text, in_data)
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
                    triples.append(Triple(subject, predicate, object_, None))
                    predicate = None
                subject = None
            elif token == "<subj>":
                current_type = TokenType.SUBJECT
                if predicate is not None:
                    triples.append(Triple(subject, predicate, object_, None))
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
                        predicate = Property(text="", url=None, label=None, description=None)

                    predicate.text += ' ' + token
                    predicate.text = predicate.text.strip()

        if subject is not None and predicate is not None and object_ is not None:
            triples.append(Triple(subject, predicate, object_, None))

        return triples

    @staticmethod
    def get_resource(token: str, original_text: str, substr_indices: dict):
        if token not in substr_indices:
            substr_indices[token] = [m.start() for m in re.finditer(f"\\b{token}\\b", original_text)]
        start_idx = substr_indices[token][0]
        substr_indices[token].pop(0)

        if len(substr_indices[token]) == 0:
            del substr_indices[token]

        return EntityMention(url=None, text="", start_idx=start_idx, end_idx=start_idx, e_type=None)


class MRebelExtractor(RelationExtractor):
    def __init__(self):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(
            "models/mrebel-large",
            local_files_only=True,
            src_lang="en_XX",
            tgt_lang="tp_XX")

        self.model = AutoModelForSeq2SeqLM.from_pretrained("models/mrebel-large", local_files_only=True,)
        self.model.to("cuda")

        self.gen_kwargs = {
            "max_length": 512,
            "length_penalty": 0,
            "num_beams": 3,
            "num_return_sequences": 3,
            "forced_bos_token_id": None,
        }

    def process(self, text: str, in_data: str) -> Optional[List[EntityMention | Triple]]:
        super().process(text, in_data)
        triples = []
        triple_hashes = set()

        sentences = [s for s in sent_tokenize(text)]

        model_inputs = self.tokenizer(sentences, max_length=512, padding=True, truncation=True, return_tensors='pt')
        generated_tokens = self.model.generate(
            model_inputs["input_ids"].to(self.model.device),
            attention_mask=model_inputs["attention_mask"].to(self.model.device),
            decoder_start_token_id=self.tokenizer.convert_tokens_to_ids("tp_XX"),
            **self.gen_kwargs,
        )

        decoded_preds = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)

        for token_string in decoded_preds:
            for triple in self.extract_triplets(token_string, text):
                triple_hash = hash(f"{triple.subject.text}:{triple.predicate.text}:{triple.object.text}")
                if triple_hash not in triple_hashes:
                    triple_hashes.add(triple_hash)
                    triples.append(triple)

        return triples

    @staticmethod
    def extract_triplets(tagged_text: str, original_text: str) -> List[Triple]:
        triplets = []
        tagged_text = tagged_text.strip()
        current = 'x'
        subject, relation, object_, object_type, subject_type = '', '', '', '', ''
        substr_indices = {}

        for token in (tagged_text
                      .replace("<s>", "")
                      .replace("<pad>", "")
                      .replace("</s>", "")
                      .replace("tp_XX", "")
                      .replace("__en__", "").split()):
            if token == "<triplet>" or token == "<relation>":
                current = 't'
                if relation != '':
                    triplets.append(Triple(
                        MRebelExtractor.get_resource(subject.strip(), subject_type),
                        Property(url=None, text=relation.strip(), label=None, description=None),
                        MRebelExtractor.get_resource(object_.strip(), object_type),
                        None))
                    relation = ''
                subject = ''
            elif token.startswith("<") and token.endswith(">"):
                if current == 't' or current == 'o':
                    current = 's'
                    if relation != '':
                        triplets.append(Triple(
                            MRebelExtractor.get_resource(subject.strip(), subject_type),
                            Property(url=None, text=relation.strip(), label=None, description=None),
                            MRebelExtractor.get_resource(object_.strip(), object_type),
                            None))
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
                    MRebelExtractor.get_resource(subject.strip(), subject_type),
                    Property(url=None, text=relation.strip(), label=None, description=None),
                    MRebelExtractor.get_resource(object_.strip(), object_type),
                    None))
        return triplets

    @staticmethod
    def get_resource(token: str, type: str):
        return EntityMention(url=None, text=token, start_idx=None, end_idx=None, e_type=type)
