clean:
	rm -rf venv

install_venv:
	python3 -m venv venv
	. venv/bin/activate; pip install --upgrade pip
	. venv/bin/activate; pip install --upgrade setuptools wheel
	. venv/bin/activate; pip install --no-cache-dir -r requirements.txt
	. venv/bin/activate; python -m spacy download en_core_web_sm
	. venv/bin/activate; python -c "import stanza; stanza.download('en')"

install_dep:
	sudo apt install libpq-dev

install: install_dep install_venv

all: install