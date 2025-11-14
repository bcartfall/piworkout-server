FROM python:3.14-slim

WORKDIR /app/backend

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    procps \
    unzip \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# install deno-js-runtime for yt-dlp
RUN VERSION=2.5.6 && \
    ARCH=x86_64-unknown-linux-gnu && \
    curl -L -o deno-${ARCH}.zip https://github.com/denoland/deno/releases/download/v${VERSION}/deno-${ARCH}.zip && \
    curl -L -o deno.zip.sha256sum https://github.com/denoland/deno/releases/download/v${VERSION}/deno-${ARCH}.zip.sha256sum && \
    sha256sum -c deno.zip.sha256sum && \
    unzip -o deno-${ARCH}.zip && \
    chmod +x deno && \
    mv -f deno /usr/local/bin/ && \
    rm deno-${ARCH}.zip deno.zip.sha256sum && \
    echo "Deno $VERSION installed and verified"

COPY ./requirements.txt /app/init/requirements.txt

RUN cd /app/init/ && pip install --no-cache-dir -r requirements.txt

CMD ["bash", "run.bash"]

# CMD [ "tail", "-f", "/app/init/requirements.txt" ]

# install ffmpeg for yt-dlp
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends \
#    git \
#    curl \
#    ffmpeg \
#    python3 \
#    python3-pip && \
#    rm -rf /var/lib/apt/lists/*

# install deno
# todo

# install pip requirements
# COPY ./requirements.txt /app/init/requirements.txt
#RUN cd /app/init/ && pip install --no-cache-dir -r requirements.txt

# copy client_secret.json
#COPY client_secret.json /app/auth/client_secret.json

#CMD ["bash", "run.bash"]