FROM ghcr.io/prefix-dev/pixi:latest
COPY . /app
WORKDIR /app
RUN pixi install
ENTRYPOINT ["pixi", "run", "dev"]
