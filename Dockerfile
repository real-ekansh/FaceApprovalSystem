version: '3.9'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      MONGODB_URL: "mongodb://mongo:27017"
      DATABASE_NAME: "face_approval_system"
    depends_on:
      - mongo
    volumes:
      - .:/app
    command: gunicorn app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

  mongo:
    image: mongo:6
    restart: always
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db

volumes:
  mongo-data:
