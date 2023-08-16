import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from waka.nlp.kg import KnowledgeGraph
from waka.nlp.kg_constructor import KnowledgeGraphConstructor

app = FastAPI(
    title="WAKA",
    description="Backend of the WAKA Assisted Knowledge Graph Authoring System",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kg_construct = KnowledgeGraphConstructor()


class Text(BaseModel):
    content: str


@app.post("/api/v1/kg", response_model=KnowledgeGraph)
async def get_kg(text: Text):
    return kg_construct.construct(text.content)


def main():
    host = "127.0.0.1"
    port = 8000
    uvicorn.run(app='serve:app', host=host,
                port=port, reload=True)


if __name__ == "__main__":
    main()
