#!/usr/bin/env bash

# use the development docker compose because it maintains the react scripts
docker compose -f compose-dev.yaml build frontend-react && docker compose -f compose-dev.yaml run frontend-react yarn build

# clean up
docker compose -f compose-dev.yaml down