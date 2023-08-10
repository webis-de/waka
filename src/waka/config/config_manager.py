import os

import yaml

from waka.config.paths import Paths


class ConfigManager:
    def __init__(self):
        self.conf = {}

        self.conf.update(ConfigManager.parse_yaml(
            os.path.join(Paths.CONFIG_DIR, "elastic.yml")))

        self.conf.update(ConfigManager.parse_yaml(
            os.path.join(Paths.CONFIG_DIR, "ppdb.yml")))

    def __getitem__(self, item):
        return self.conf[item]

    @staticmethod
    def parse_yaml(path):
        with open(path, "r") as in_file:
            return yaml.safe_load(in_file)

