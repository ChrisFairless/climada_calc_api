FROM crease/climada

ENV PYTHONUNBUFFERED 1
ENV DOCKER_CONTAINER 1

WORKDIR /
COPY requirements.txt /requirements.txt
RUN pip install --no-cache -r /requirements.txt

COPY . /climada_calc_api
COPY ./climada.conf ~/climada.conf
RUN touch /climada_calc_api/.env
WORKDIR /climada_calc_api

