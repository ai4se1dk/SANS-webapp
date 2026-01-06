#!/bin/bash

mkdir -p ~/.streamlit/

echo "[general]
email = \"\"
" > ~/.streamlit/credentials.toml

echo "[server]
headless = true
enableCORS = false
port = $PORT
" > ~/.streamlit/config.toml
