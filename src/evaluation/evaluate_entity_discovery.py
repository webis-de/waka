import multiprocessing
from typing import List

import click

from evaluation.corpora.red_fm import RedFM
from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import EnsembleNER
from waka.nlp.kg import EntityMention
from waka.nlp.semantics import EntitySentenceBert
from waka.nlp.text_processor import Pipeline


@click.command()
@click.option("-s", "--stage", type=click.Choice(["ner", "el", "rerank"]), default="ner")
def main(stage: str) -> None:
    multiprocessing.set_start_method("spawn")
    dataset = RedFM()

    el_pipeline = Pipeline[List[EntityMention]]()
    el_pipeline.add_processor(EnsembleNER)

    if stage == "el":
        el_pipeline.add_processor(ElasticEntityLinker)
    if stage == "rerank":
        el_pipeline.add_processor(ElasticEntityLinker)
        el_pipeline.add_processor(EntitySentenceBert)
    el_pipeline.start()
    macro_prec, macro_rec, macro_f1 = [], [], []

    des_entities = []
    computed_entities = []
    min_scores = []

    while dataset.has_next():
        kg = dataset.next()
        el_pipeline.process(kg.text)

        entities = el_pipeline.get()

        if stage == "rerank":
            aggregated = []
            for entity in entities:
                aggregated.extend(entity.mentions)
            entities = list(sorted(set(aggregated), key=lambda x: x.score, reverse=True))

        result = EntityMention.eval(kg.entity_mentions, entities)

        correct_entities = [e for e in entities if e in kg.entities]
        if len(correct_entities) > 0:
            min_score = min([e.score for e in correct_entities])
            min_scores.append(min_score)

        des_entities.extend(kg.entity_mentions)
        computed_entities.extend(entities)

        macro_prec.append(result["precision"])
        macro_rec.append(result["recall"])
        macro_f1.append(result["f1"])

    micro_result = EntityMention.eval(des_entities, computed_entities)
    print(f"Macro-Precision: {sum(macro_prec) / len(macro_prec):.4f} "
          f"Macro-Recall: {sum(macro_rec) / len(macro_rec):.4f} "
          f"Macro-F1: {sum(macro_f1) / len(macro_f1):.4f} ")
    print(f"Micro-Precision: {micro_result['precision']:.4f} "
          f"Micro-Recall: {micro_result['recall']:.4f} "
          f"Micro-F1: {micro_result['f1']:.4f} ")

    el_pipeline.end()
    el_pipeline.join()


if __name__ == '__main__':
    main()
