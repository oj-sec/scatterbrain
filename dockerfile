FROM node:18-alpine as build
WORKDIR /app/client
COPY ./client/ .
RUN npm install
RUN npm run build

FROM python:3.11-slim as server
RUN apt-get update && apt-get install -y gcc g++ build-essential
WORKDIR /app/server
COPY ./server/ .
COPY --from=build /app/client/build /app/client/build
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python3", "server.py"] 