@echo off
REM Script to start Langfuse services, universalis-chromadb Docker image, and MongoDB Compass
REM Langfuse directory -  D:\dev_2\pyscrai_universalis\langfuse 

REM Create Langfuse services
@REM cd /d "%~dp0langfuse"
@REM docker compose up -d

@REM pip install -e ./pyscrai

REM Start universalis-chromadb Docker image (detached)
docker start universalis-chromadb

REM Start MongoDB Compass
mongod --dbpath="D:\dev_2\pyscrai_universalis\data\mongoDB"
@REM start "" "C:\Users\tyler\AppData\Local\MongoDBCompass\MongoDBCompass.exe"
