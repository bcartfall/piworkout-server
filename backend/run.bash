#!/usr/bin/env bash

if [ $APP_ENV = "development" ]
then
    python3 -u autoreload.py
else
    python3 -u app.py
fi