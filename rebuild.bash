#!/usr/bin/env bash
cd "$(dirname "$0")"

# rebuild
/usr/local/bin/docker-compose build --no-cache && /usr/local/bin/docker-compose down && /usr/local/bin/docker-compose up -d