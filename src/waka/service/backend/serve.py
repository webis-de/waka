import multiprocessing

import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from waka.nlp.kg import KnowledgeGraph
from waka.nlp.kg_construction import KGConstructor


class Text(BaseModel):
    content: str


def app():
    app = FastAPI(
        title="WAKA",
        description="Backend of the WAKA Assisted Knowledge Graph Authoring System",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount(
        "/static",
        StaticFiles(directory="web/static"),
        name="static"
    )

    app.include_router(KGConstructionRouter())

    return app


class KGConstructionRouter(APIRouter):
    def __init__(self):
        super().__init__()
        self.kg_construct = KGConstructor()

        self.add_api_route(path="/api/v1/kg",
                           endpoint=self.create_kg,
                           response_model=KnowledgeGraph,
                           methods=["POST"])

        self.add_api_route("/",
                           endpoint=lambda: RedirectResponse(url="/static/index.html"),
                           methods=["GET"])

    async def create_kg(self, text: Text) -> KnowledgeGraph:
        return self.kg_construct.construct(text.content)


def main():
    multiprocessing.set_start_method("spawn")

    host = "0.0.0.0"
    port = 8000

    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    uvicorn.run(app='serve:app', host=host,
                port=port, reload=False, lifespan="on", log_config=log_config)


if __name__ == "__main__":
    main()
