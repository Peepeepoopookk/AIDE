FROM alpine:latest

RUN apk add --no-cache wget unzip && \
    mkdir /pb && \
    wget https://github.com/pocketbase/pocketbase/releases/download/v0.36.7/pocketbase_0.36.7_linux_amd64.zip && \
    unzip pocketbase_0.36.7_linux_amd64.zip -d /pb && \
    rm pocketbase_0.36.7_linux_amd64.zip

EXPOSE 8090
CMD ["/pb/pocketbase", "serve", "--http=0.0.0.0:8090"]
