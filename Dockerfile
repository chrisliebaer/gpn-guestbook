FROM ghcr.io/prefix-dev/pixi:latest
COPY . /app
WORKDIR /app
RUN pixi install --locked
ENTRYPOINT ["pixi", "run", "dev"]
