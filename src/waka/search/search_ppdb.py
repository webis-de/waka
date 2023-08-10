import re
from nltk.corpus import wordnet

from elastic_client import ElasticClient
from waka.config.config_manager import ConfigManager


def to_al_num(s: str, keep_space=False):
    if keep_space:
        return re.sub('[^A-Za-z0-9\\s]+', '', s).strip()

    return re.sub('[^A-Za-z0-9]+', '', s).strip()


def main():
    conf = ConfigManager()
    client = ElasticClient(conf).get_client()
    query = "artistic fields"
    res = client.search(index=conf["elastic"]["ppdb_index"], query={"match": {"phrase": query}}, size=1000)
    for hit in res["hits"]["hits"]:
        if to_al_num(hit["_source"]["phrase"]) == query:
            print(to_al_num(hit["_source"]["equivalent"], keep_space=True))

    print("----------------")

    for syn in wordnet.synsets(query):
        for l in syn.lemmas():
            print(l.name())

    client.close()


if __name__ == '__main__':
    main()
