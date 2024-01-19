#!/usr/bin/env bash

# docker compose -f compose-dev.yaml build frontend-react && docker compose -f compose-dev.yaml up frontend-react
# docker compose -f compose-dev.yaml build frontend-nginx && docker compose -f compose-dev.yaml up frontend-nginx
# docker compose -f compose-dev.yaml build backend && docker compose -f compose-dev.yaml up backend

# run all
docker-compose -f compose-dev.yaml build && docker-compose -f compose-dev.yaml up