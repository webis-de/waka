import copy
import logging
import random
import sys
import time

from evaluation.corpora.red_fm import RedFM
from waka.nlp.entity_linking import ElasticEntityLinker
from waka.nlp.kg import EntityMention


def main():
    logging.getLogger("elastic_transport.transport").setLevel(logging.ERROR)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
    el_start_conf = (3, 0.2, 20, 20)
    random.seed(time.time())
    direction = [random.choice([1, -1]), random.choice([1, -1]), random.choice([1, -1]), random.choice([1, -1])]
    modifier = (
        lambda: 1,
        lambda: round(random.uniform(0.1, 1.0), 2),
        lambda: random.randint(1, 5),
        lambda: random.randint(1, 5)
    )

    current_conf = el_start_conf
    best_score = 0
    best_scores = None
    best_conf = None
    param = None
    run = 0
    no_update = 0
    tested_confs = set()

    while True:
        el = ElasticEntityLinker(*current_conf)
        macro_prec, macro_rec, macro_f1, macro_f2 = [], [], [], []
        dataset = RedFM(dev=True, train=False, test=False)

        while dataset.has_next():
            kg = dataset.next()

            in_data = [EntityMention(
                start_idx=e.start_idx,
                end_idx=e.end_idx,
                e_type=e.e_type,
                text=e.text,
                url=None) for e in copy.deepcopy(kg.entity_mentions)]
            entities = el.process(kg.text, in_data)

            result = EntityMention.eval(kg.entity_mentions, entities)

            macro_prec.append(result["precision"])
            macro_rec.append(result["recall"])
            macro_f1.append(result["f1"])
            try:
                macro_f2.append((1+2**2) * (result["precision"] * result["recall"]) / ((2**2 * result["precision"]) + result["recall"]))
            except ZeroDivisionError:
                macro_f2.append(0)

        precision = sum(macro_prec) / len(macro_prec)
        recall = sum(macro_rec) / len(macro_rec)
        f1 = sum(macro_f1) / len(macro_f1)
        f2 = sum(macro_f2) / len(macro_f2)
        metric = recall
        print(f"Run {run}: {current_conf} -> {metric}")

        if metric > best_score:
            best_score = metric
            best_scores = (precision, recall, f1, f2)
            best_conf = current_conf
            no_update = 0
        else:
            if param is not None:
                direction[param] *= -1
            no_update += 1

        if no_update >= 20:
            print(f"Best config: {best_conf} -> {best_scores}")
            sys.exit(0)

        tested_confs.add(current_conf)

        while current_conf in tested_confs:
            param = random.randint(0, len(el_start_conf) - 1)
            current_conf = list(copy.deepcopy(best_conf))
            current_conf[param] += direction[param] * modifier[param]()
            current_conf[0] = max(1, current_conf[0])
            current_conf[1] = round(max(0.01, current_conf[1]), 2)
            current_conf[2] = max(1, current_conf[2])
            current_conf[3] = max(1, current_conf[3])
            current_conf = tuple(current_conf)

        run += 1


if __name__ == '__main__':
    main()
