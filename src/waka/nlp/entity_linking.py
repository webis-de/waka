import abc
import asyncio
import copy
from typing import List

import aiohttp
import pycountry
from cachetools import LFUCache

from waka.nlp.kg import EntityMention, LinkedEntity
from waka.nlp.text_processor import TextProcessor


class EntityLinker(TextProcessor[List[EntityMention], List[LinkedEntity]], metaclass=abc.ABCMeta):
    pass


class ElasticEntityLinker(EntityLinker):
    def __init__(self):
        super().__init__()
        self.search_endpoint = "https://metareal-kb.web.webis.de/api/v1/kb/entity/search"
        self.cache = LFUCache(maxsize=512)

    def process(self, text: str, in_data: List[EntityMention]) -> List[LinkedEntity]:
        super().process(text, in_data)
        request_entities = []
        linked_entities = []

        for entity in in_data:
            if entity.text in self.cache:
                linked_entities.extend(copy.deepcopy(self.cache[entity.text]))
            else:
                if entity.url is not None:
                    linked_entities.append(LinkedEntity(
                        text=entity.text,
                        url=entity.url,
                        start_idx=entity.start_idx,
                        end_idx=entity.end_idx,
                        e_type=entity.e_type,
                        label=None,
                        score=1.0,
                        description=None
                    ))
                else:
                    request_entities.append(entity)

        results = asyncio.run(self.send_all(request_entities))

        if isinstance(results, List):
            for result in results:
                if not isinstance(result, List):
                    print(result)

                if len(result) > 0:
                    self.cache[result[0].text] = copy.deepcopy(result)

                linked_entities.extend(result)
        else:
            self.logger.error(results)

        return linked_entities

    async def send_all(self, entities: List[EntityMention]) -> tuple[BaseException | List[List[LinkedEntity]]]:
        results = []
        async with aiohttp.ClientSession() as session:
            for entity in entities:
                results.append(self.send_request(session, entity))

            results = await asyncio.gather(*results, return_exceptions=True)

        return results

    async def send_request(self, session: aiohttp.ClientSession, entity: EntityMention) -> List[LinkedEntity]:
        retrieved_entities = []
        queries = []
        try:
            queries.extend([c.name for c in pycountry.countries.search_fuzzy(entity.text)])
            if len(queries) > 3:
                queries.clear()
        except LookupError:
            pass

        queries.extend([x.strip() for x in entity.text.split(",")])
        if entity.text.replace("'s", "") != entity.text:
            queries.append(entity.text.replace("'s", ""))

        for query in queries:
            async with session.get(self.search_endpoint, params={"q": query}) as response:
                body = await response.json()

                if body["status"] == "success":
                    for e in body["data"]:
                        try:
                            if e["label"].lower().startswith('category:'):
                                continue
                        except AttributeError:
                            pass

                        retrieved_entities.append(LinkedEntity(
                            url=e["id"],
                            start_idx=entity.start_idx,
                            end_idx=entity.end_idx,
                            text=entity.text,
                            label=e["label"],
                            score=e["score"] / 305,
                            e_type=entity.e_type,
                            description=e["description"]))

        return retrieved_entities
