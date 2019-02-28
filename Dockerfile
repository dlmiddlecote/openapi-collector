FROM nginx:1.15.8

RUN apt-get update && apt-get -y install inotify-tools

COPY ./docker/nginx.conf /etc/nginx/
COPY ./docker/entrypoint.sh /entrypoint.sh

ENTRYPOINT /entrypoint.sh
