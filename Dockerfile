FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel
LABEL authors="Marcel Gohsen"

SHELL ["/bin/bash", "-c"]

ENV TZ="Europe/Berlin"
ENV ES_API_KEY=RmFjZjdwQUJZekJBQWFBSmNoSFo6TkFoQ2hVYkdSVDZqeU1Jd3FBNmhSQQ==
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /waka/

RUN apt update && apt install -y libpq-dev libfreetype-dev libpng-dev git-lfs && git lfs install
RUN git -C models/mrebel-large pull || git clone https://huggingface.co/Babelscape/mrebel-large/ models/mrebel-large
RUN git -C models/bart-large-mnli pull || git clone https://huggingface.co/facebook/bart-large-mnli models/bart-large-mnli
RUN git -C models/all-distilroberta-v1 pull || git clone https://huggingface.co/sentence-transformers/all-distilroberta-v1 models/all-distilroberta-v1

COPY Makefile requirements.txt /waka/

RUN make clean install_novenv

COPY config.json  /waka/
COPY src/ /waka/src/
COPY web/ /waka/web/
COPY data/countries.csv /waka/data/countries.csv

EXPOSE 8000

CMD ["make", "run_novenv"]