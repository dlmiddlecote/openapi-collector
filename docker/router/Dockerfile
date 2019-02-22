FROM nginx:1.15.8

RUN apt-get update && apt-get -y install inotify-tools

COPY ./docker/router/nginx.conf /etc/nginx/
COPY ./docker/router/entrypoint.sh /entrypoint.sh

ENTRYPOINT /entrypoint.sh
