import multiprocessing
from typing import List

from evaluation.corpora.red_fm import RedFM
from waka.nlp.kg import Property, Triple
from waka.nlp.relation_extraction import MRebelExtractor
from waka.nlp.text_processor import Pipeline


def main():
    multiprocessing.set_start_method("spawn")
    dataset = RedFM()
    rl_pipeline = Pipeline[List[Triple]]()
    rl_pipeline.add_processor(MRebelExtractor)
    # rl_pipeline.add_processor(ElasticRelationLinker)
    rl_pipeline.start()
    macro_prec, macro_rec, macro_f1 = [], [], []

    des_triples = []
    computed_triples = []

    while dataset.has_next():
        kg = dataset.next()
        rl_pipeline.process(kg.text)

        triples = rl_pipeline.get()

        for t in kg.triples:
            t.predicate.url = None

        result = Property.eval(kg.triples, triples)
        des_triples.extend(kg.triples)
        computed_triples.extend(triples)

        macro_prec.append(result["precision"])
        macro_rec.append(result["recall"])
        macro_f1.append(result["f1"])

    micro_result = Property.eval(des_triples, computed_triples)
    print(f"Macro-Precision: {sum(macro_prec) / len(macro_prec):.4f} "
          f"Macro-Recall: {sum(macro_rec) / len(macro_rec):.4f} "
          f"Macro-F1: {sum(macro_f1) / len(macro_f1):.4f} ")
    print(f"Micro-Precision: {micro_result['precision']:.4f} "
          f"Micro-Recall: {micro_result['recall']:.4f} "
          f"Micro-F1: {micro_result['f1']:.4f} ")

    rl_pipeline.end()
    rl_pipeline.join()


if __name__ == '__main__':
    main()
