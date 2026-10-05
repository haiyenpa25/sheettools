FROM python:3.12-slim-bookworm
ARG HOMR_REVISION=560ca5ce254db129b1b2167598bdc7a20ac5d6b0
RUN apt-get update && apt-get install -y --no-install-recommends git libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/liebharc/homr.git /opt/homr && cd /opt/homr && git checkout ${HOMR_REVISION} && pip install --no-cache-dir '.[cpu]'
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
RUN homr --init --no-title
RUN chown -R 33:33 /opt/homr /usr/local/lib/python3.12/site-packages/homr
RUN pip freeze > /opt/runtime-requirements.txt
COPY workers /opt/sheettools/workers
CMD ["python", "/opt/sheettools/workers/external_omr/worker.py", "--engine", "homr"]
