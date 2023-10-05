import multiprocessing

from evaluation.datasets.red_fm import RedFM
from waka.nlp.kg import KnowledgeGraph
from waka.nlp.kg_construction import KGConstructor


def main():
    multiprocessing.set_start_method("spawn")
    dataset = RedFM()
    kg_construct = KGConstructor()
    macro_prec, macro_rec, macro_f1 = [], [], []
    desired_triples = []
    computed_triples = []

    while dataset.has_next():
        kg = dataset.next()
        comp_kg = kg_construct.construct(kg.text)

        result = KnowledgeGraph.eval(kg.triples, comp_kg.triples)
        desired_triples.extend(kg.triples)
        computed_triples.extend(comp_kg.triples)

        macro_prec.append(result["precision"])
        macro_rec.append(result["recall"])
        macro_f1.append(result["f1"])

    micro_result = KnowledgeGraph.eval(desired_triples, computed_triples)
    print(f"Macro-Precision: {sum(macro_prec) / len(macro_prec):.4f} "
          f"Macro-Recall: {sum(macro_rec) / len(macro_rec):.4f} "
          f"Macro-F1: {sum(macro_f1) / len(macro_f1):.4f} ")
    print(f"Micro-Precision: {micro_result['precision']:.4f} "
          f"Micro-Recall: {micro_result['recall']:.4f} "
          f"Micro-F1: {micro_result['f1']:.4f} ")


if __name__ == '__main__':
    main()
