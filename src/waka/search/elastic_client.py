from elasticsearch import Elasticsearch, RequestsHttpConnection

from waka.config.config_manager import ConfigManager


class ElasticClient:
    def __init__(self, conf):
        self._es = Elasticsearch([f"{conf['elastic']['host']}:{conf['elastic']['port']}"],
                                 api_key=conf["elastic"]["auth"])

    def get_client(self):
        return self._es

    def close(self):
        self._es.close()
