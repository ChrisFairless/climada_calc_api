FROM crease/climada:v3.2.0

ENV PYTHONUNBUFFERED 1
ENV DOCKER_CONTAINER 1

RUN apt-get update

WORKDIR /
COPY requirements.txt /requirements.txt
RUN pip install --no-cache -r /requirements.txt

COPY . /climada_calc_api
RUN chmod -R 755 /climada_calc_api
COPY ./climada.conf ~/climada.conf
WORKDIR /climada_calc_api
