SHELL := /bin/bash

clean:
	rm -rf venv

install_venv:
	python3 -m venv venv
	. venv/bin/activate; pip install --upgrade pip
	. venv/bin/activate; pip install --upgrade setuptools wheel
	. venv/bin/activate; pip install --no-cache-dir -r requirements.txt
	. venv/bin/activate; python -m spacy download en_core_web_sm
	. venv/bin/activate; python -c "import stanza; stanza.download('en')"
	. venv/bin/activate; python -c "import nltk; nltk.download('punkt')"

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
	export PYTHONPATH="$(shell pwd)/src" && source venv/bin/activate && python src/waka/service/backend/serve.py