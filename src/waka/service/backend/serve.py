# from ctypes import Union
import json
from typing import Optional, List


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# nlp_model_en = spacy.load("en_core_web_sm")
# nlp_model_en.add_pipe("entityfishing")

app = FastAPI(
    title="Knowledge Graph Authoring System",
    description="Backend implementation of Knowledge Graph Authoring System",
    version="0.7.0",
    openapi_url="/api/v1/openapi.json"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Text(BaseModel):
    content: Optional[str] = None


class subject(BaseModel):
    entity: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    type_: Optional[str] = None


class predicate(BaseModel):
    entity: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    type_: Optional[str] = None


class object_(BaseModel):
    entity: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    type_: Optional[str] = None


class Triple(BaseModel):
    entity: str
    start: int
    end: int
    type_: str


class Model(BaseModel):
    triples: Optional[List[List[Triple]]] = None


subj_list = []
pred_list = []
obj_list = []


@app.post("/api/v1/entity_linking")
async def entity_linking(text: str):
    nlp = spacy.blank("en")
    nlp.add_pipe('opentapioca')
    doc = nlp(text)
    for span in doc.ents:
        print(span.kb_id_)
        return (span.text, span.kb_id_, span.label_)


@app.post("/api/v1/submit", summary="Submit the user changed to backend")
async def build_triple(triples: Model):
    data = triples.dict()
    data = data["triples"]
    print(data)

    nodes = []
    edges = []

    nodes_map = {}

    id = 1

    for lst in data:
        for tup in lst:
            entity = tup["entity"]
            type_ = tup["type_"]
            if type_ == "subj":
                entity_subj = entity
            elif type_ == "pred":
                entity_pred = entity
            elif type_ == "obj":
                entity_obj = entity

        if entity_subj not in nodes_map:
            nodes.append({"id": id, "label": entity_subj})
            nodes_map[entity_subj] = id
            id += 1

        if entity_obj not in nodes_map:
            nodes.append({"id": id, "label": entity_obj})
            nodes_map[entity_obj] = id
            id += 1

        id1 = nodes_map[entity_subj]
        id2 = nodes_map[entity_obj]
        edges.append(
            {"from": id1, "to": id2, "label": entity_pred, "arrows": "to"})
    # print(nodes)
    # print("=============")
    # print(edges)
    return nodes, edges


@app.post("/api/v1/text", summary="Return the user input text to backend for processing")
async def text(text: Text):
    text_ = text.dict()["content"]
    doc_en = nlp_model_en(text_)
    wikilist = []
    for span in doc_en.ents:
        wikilist.append((span.text, span._.kb_qid, span._.url_wikidata))
        # return ((span.text, span._.kb_qid, span._.url_wikidata))
    print(wikilist)
    return wikilist


@ app.post("/api/v1/subj", response_model=subject, summary="Set selected entity to subject")
async def set_subject(subject: subject):
    subj_list.append(json.loads(subject.json()))
    # with open("/root/kg/backend/assets/subject.json", "a") as f:
    #     f.write(subject.json())
    # print(type(json.loads(subject.json())))
    print(subj_list)
    return subject


@ app.post("/api/v1/pred", response_model=predicate, summary="Set selected entity to predicate")
async def set_predicate(predicate: predicate):
    pred_list.append(json.loads(predicate.json()))
    # with open("/root/kg/backend/assets/predicate.json", "a") as f:
    #     f.write(predicate.json())
    print(pred_list)
    return predicate


@ app.post("/api/v1/obj", response_model=object_, summary="Set selected entity to object")
async def set_object(object_: object_):
    obj_list.append(json.loads(object_.json()))
    # with open("/root/kg/backend/assets/object.json", "a") as f:
    #     f.write(object_.json())
    print(obj_list)
    return object_


@ app.get("/api/v1/reset", summary="Reset the user input include backend data")
async def reset():
    subj_list.clear()
    pred_list.clear()
    obj_list.clear()
    print(subj_list, pred_list, obj_list)
    return {"result": "reset success"}


@ app.get("/api/v1/link", summary="Link the user selected entities")
async def link():
    return {"hello": "world"}


# @app.get("/")
# def read_root():
#     return {"Hello": "World"}


@ app.get("/api/v1/export", summary="Export the Knowledge Graph, parameters: format(json/turtle)")
def read_server():
    return "Export Success"


@ app.delete("/api/v1/ent", summary="Delete the user selected entity")
def delete_ent():
    return "Export Success"


def start_server(host, port):
    import uvicorn
    uvicorn.run(app='serve:app', host=host,
                port=port, reload=True)


def main():
    start_server('127.0.0.1', 8000)


if __name__ == "__main__":
    main()
