SHELL := /bin/bash

VERSION=$(shell cat config.json | jq .version | tr -d '"')

clean:
	rm -rf venv

docker:
	docker build -t registry.webis.de/code-research/conversational-search/assisted-knowledge-graph-authoring:latest -t registry.webis.de/code-research/conversational-search/assisted-knowledge-graph-authoring:$(VERSION) .
	docker push registry.webis.de/code-research/conversational-search/assisted-knowledge-graph-authoring:latest
	docker push registry.webis.de/code-research/conversational-search/assisted-knowledge-graph-authoring:$(VERSION)

install_venv:
	python3 -m venv venv
	. venv/bin/activate; pip install --upgrade pip
	. venv/bin/activate; pip install --upgrade setuptools wheel
	. venv/bin/activate; pip install --no-cache-dir -r requirements.txt
	. venv/bin/activate; python -m spacy download en_core_web_trf
	. venv/bin/activate; python -c "import stanza; stanza.download('en')"
	. venv/bin/activate; python -c "import nltk; nltk.download('punkt')"

install_novenv:
	python3 -m pip install --upgrade pip
	python3 -m pip install --upgrade setuptools wheel
	python3 -m pip install --no-cache-dir -r requirements.txt
	python3 -m spacy download en_core_web_trf
	python3 -c "import stanza; stanza.download('en')"
	python3 -c "import nltk; nltk.download('punkt')"

install_dep:
	sudo apt install libpq-dev libfreetype-dev libpng-dev git-lfs

install: install_dep install_venv load_models

load_models:
	git lfs install
	git -C models/mrebel-large pull || git clone https://huggingface.co/Babelscape/mrebel-large/ models/mrebel-large
	git -C models/bart-large-mnli pull || git clone https://huggingface.co/facebook/bart-large-mnli models/bart-large-mnli
	git -C models/all-distilroberta-v1 pull || git clone https://huggingface.co/sentence-transformers/all-distilroberta-v1 models/all-distilroberta-v1

all: install

run:
	export PYTHONPATH="$(shell pwd)/src" ES_API_KEY=RmFjZjdwQUJZekJBQWFBSmNoSFo6TkFoQ2hVYkdSVDZqeU1Jd3FBNmhSQQ== && source venv/bin/activate && python src/waka/service/backend/serve.py

run_novenv:
	export PYTHONPATH="$(shell pwd)/src" && python3 src/waka/service/backend/serve.py