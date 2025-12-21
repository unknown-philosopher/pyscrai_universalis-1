@echo off
REM Script to start Langfuse services, universalis-chromadb Docker image, and MongoDB Compass
REM Langfuse directory -  D:\dev_2\pyscrai_universalis\langfuse 

REM Create Langfuse services
cd /d "%~dp0langfuse"
docker compose up -d

REM Start universalis-chromadb Docker image (detached)
docker start universalis-chromadb

REM Start MongoDB Compass
start "" "C:\Users\tyler\AppData\Local\MongoDBCompass\MongoDBCompass.exe"
