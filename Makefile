install:
	python3 -m venv venv
	. venv/bin/activate; pip install -r requirements.txt
	. venv/bin/activate; python -m spacy download en_core_web_sm

all: install