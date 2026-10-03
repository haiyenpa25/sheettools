# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS frontend
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig.json vite.config.ts ./
COPY resources ./resources
COPY public ./public
RUN npm run build

FROM ubuntu:24.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG AUDIVERIS_VERSION=5.11.0
ARG AUDIVERIS_DEB=Audiveris-5.11.0-ubuntu24.04-x86_64.deb

ENV APP_ENV=production \
    APP_DEBUG=false \
    PYTHON_BIN=/opt/venv/bin/python \
    JAVA_BIN=java \
    AUDIVERIS_EXE=/opt/audiveris/bin/Audiveris \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata \
    TESSERACT_BIN=tesseract \
    OMR_TIMEOUT_SECONDS=300 \
    APACHE_DOCUMENT_ROOT=/var/www/html \
    PATH=/opt/venv/bin:/opt/audiveris/bin:${PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        apache2 ca-certificates curl \
        php8.3 php8.3-cli libapache2-mod-php8.3 php8.3-curl php8.3-mbstring \
        php8.3-xml php8.3-zip \
        python3 python3-pip python3-venv \
        openjdk-21-jre-headless \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie \
        poppler-utils nodejs npm \
        libglib2.0-0 libgl1 libxrender1 libxtst6 libxi6 libfreetype6 fontconfig \
        libasound2t64 \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# Extract the official package without running its desktop-menu post-install hook;
# the container uses only Audiveris' headless CLI.
RUN curl -fsSL -o /tmp/audiveris.deb \
        "https://github.com/Audiveris/audiveris/releases/download/${AUDIVERIS_VERSION}/${AUDIVERIS_DEB}" \
    && dpkg-deb -x /tmp/audiveris.deb / \
    && rm -f /tmp/audiveris.deb \
    && test -x /opt/audiveris/bin/Audiveris

# Audiveris probes GTK through JNA even for non-interactive batch commands.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgtk-3-0t64 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html

COPY docker/requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

COPY app ./app
COPY config ./config
COPY workers ./workers
COPY tests ./tests
COPY ["001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml", "./"]
COPY api.php health_check.php composer.json ./
COPY --from=frontend /src/dist ./
COPY docker/apache-sheettools.conf /etc/apache2/sites-available/000-default.conf
COPY docker/entrypoint.sh /usr/local/bin/sheettools-entrypoint

RUN a2enmod rewrite headers \
    && chmod +x /usr/local/bin/sheettools-entrypoint \
    && mkdir -p storage/projects storage/songbooks storage/exports storage/cache storage/logs \
    && chown -R www-data:www-data /var/www/html/storage \
    && printf 'upload_max_filesize=50M\npost_max_size=52M\nmax_execution_time=600\nmemory_limit=1024M\n' \
        > /etc/php/8.3/apache2/conf.d/99-sheettools.ini

EXPOSE 80
VOLUME ["/var/www/html/storage"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1/api/health >/dev/null || exit 1

ENTRYPOINT ["sheettools-entrypoint"]
CMD ["apachectl", "-D", "FOREGROUND"]
