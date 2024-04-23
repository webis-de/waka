FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel
LABEL authors="Marcel Gohsen"

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive TZ="Europe/Berlin"

COPY src/ /waka/src/
COPY web/ /waka/web/
COPY Makefile requirements.txt /waka/

WORKDIR /waka/

RUN apt update && apt install -y libpq-dev libfreetype-dev libpng-dev && make clean install_venv

EXPOSE 8000

CMD ["make", "run"]