# WAKA: Webis Assisted Knowledge Graph Authoring

Demo of the WAKA application to construct and author knowledge graphs from unstructured text. 

## Install

```shell
make clean install
```

## Run server

```shell
source venv/bin/activate
export PYTHONPATH="src" && python waka/service/backend/serve.py
```