FROM python:3.12-slim-bookworm
ARG CLARITY_REVISION=c6bb8a4d2a5b52842a9c41bd0f761f58d02f6f82
RUN apt-get update && apt-get install -y --no-install-recommends git libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/clquwu/Clarity-OMR.git /opt/clarity && cd /opt/clarity && git checkout ${CLARITY_REVISION} && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements.txt
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 HF_HOME=/var/www/html/storage/cache/clarity-hf
RUN chown -R 33:33 /opt/clarity
RUN pip freeze > /opt/runtime-requirements.txt
COPY workers /opt/sheettools/workers
CMD ["python", "/opt/sheettools/workers/external_omr/worker.py", "--engine", "clarity"]
