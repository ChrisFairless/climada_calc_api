FROM crease/climada

ENV PYTHONUNBUFFERED 1
ENV DOCKER_CONTAINER 1

WORKDIR /
COPY requirements.txt /requirements.txt
RUN pip install --no-cache -r /requirements.txt

COPY . /climada_calc_api
COPY ./climada.conf ~/climada.conf
WORKDIR /climada_calc_api
RUN touch .env
RUN bash -c "python manage.py makemigrations calc_api --noinput && \
             python manage.py migrate calc_api --noinput && \
             python manage.py generate_sample_data && \
             python manage.py generate_measure_data"

