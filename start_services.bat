@echo off
REM Script to start Langfuse services, universalis-chromadb Docker image, and MongoDB Compass
REM Langfuse directory -  D:\dev_2\pyscrai_universalis\langfuse 

REM Create Langfuse services
@REM cd /d "%~dp0langfuse"
@REM docker compose up -d

@REM pip install -e ./pyscrai

REM Start universalis-chromadb Docker image (detached)
docker start pyscrai-chromadb

REM Start MongoDB Compass
mongod --dbpath="D:\dev_2\pyscrai_universalis\database\mongoDB"

@REM start "" "C:\Users\tyler\AppData\Local\MongoDBCompass\MongoDBCompass.exe"

@REM docker run --name=pyscrai-chromadb --hostname=0dd174c70ce6 --env=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin --env=ASAN_OPTIONS= --env=ASAN_SYMBOLIZER_PATH= --env=RUST_BACKTRACE=0 --volume=D:\dev_2\pyscrai_universalis\database\chroma-data:/data --network=bridge -p 8000:8000 --restart=no --runtime=runc -d chromadb/chroma