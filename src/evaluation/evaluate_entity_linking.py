import multiprocessing
from typing import List

from evaluation.corpora.red_fm import RedFM
from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.entity_recognition import EnsembleNER
from waka.nlp.kg import Entity
from waka.nlp.text_processor import Pipeline


def main():
    multiprocessing.set_start_method("spawn")
    dataset = RedFM()
    el_pipeline = Pipeline[List[Entity]]()
    el_pipeline.add_processor(EnsembleNER)
    el_pipeline.add_processor(ElasticEntityLinker)
    # el_pipeline.add_processor(EntitySentenceBert)
    el_pipeline.start()
    macro_prec, macro_rec, macro_f1 = [], [], []

    des_entities = []
    computed_entities = []

    while dataset.has_next():
        kg = dataset.next()
        el_pipeline.process(kg.text)

        entities = el_pipeline.get()

        result = Entity.eval(kg.entities, entities)
        des_entities.extend(kg.entities)
        computed_entities.extend(entities)

        macro_prec.append(result["precision"])
        macro_rec.append(result["recall"])
        macro_f1.append(result["f1"])

    micro_result = Entity.eval(des_entities, computed_entities)
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
