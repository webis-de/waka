import json
import os
import time

from elasticsearch.helpers import bulk

from waka.config.config_manager import ConfigManager
from waka.config.paths import Paths
from waka.search.elastic_client import ElasticClient


def main():
    conf = ConfigManager()
    with open(os.path.join(Paths.CONFIG_DIR, "ppdb-mapping.json"), "r") as in_file:
        mapping = json.load(in_file)

    conf = ConfigManager()
    elastic_client = ElasticClient(conf).get_client()
    index_name = conf["elastic"]["ppdb_index"]

    if elastic_client.indices.exists(index=index_name):
        elastic_client.indices.delete(index=index_name)

    elastic_client.indices.create(index=index_name, mappings=mapping)
    actions = []
    print_time = time.time()
    count_indexed = 0
    count_read = 0

    with open(conf["ppdb"]["path"], "r") as in_file:
        for line in in_file:
            count_read += 1
            comp = line.strip().split(" ||| ")
            if comp[-1] != "Equivalence":
                continue

            doc = {
                "phrase": comp[1],
                "equivalent": comp[2]
            }

            actions.append({"_index": index_name,
                            "_op_type": "index",
                            "_source": doc})
            count_indexed += 1

            if len(actions) >= conf["elastic"]["index_batch_size"]:
                bulk(elastic_client, actions)
                actions.clear()

            if time.time() - print_time >= 1.:
                print(f"\rIndexed: {count_indexed} | Read: {count_read}", end="")
                print_time = time.time()

    if len(actions) > 0:
        bulk(elastic_client, actions)
        actions.clear()

    print(f"\rIndexed: {count_indexed} | Read: {count_read}", end="")

    elastic_client.close()


if __name__ == '__main__':
    main()
