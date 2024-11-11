#!/usr/bin/env bash

cd "$(dirname "$0")"
/usr/local/bin/docker-compose down && /usr/local/bin/docker-compose up -d
