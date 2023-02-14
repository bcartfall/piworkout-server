FROM python:3-alpine

WORKDIR /app/backend

# install ffmpeg for yt-dlp
RUN apk add ffmpeg

# install pip requirements
COPY ./requirements.txt /app/init/requirements.txt
RUN cd /app/init/ && pip install --no-cache-dir -r requirements.txt

# copy client_secret.json
COPY client_secret.json /app/auth/client_secret.json

CMD ["sh", "run.bash"]