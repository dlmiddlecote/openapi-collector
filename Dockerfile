FROM nginx:1.15.8

COPY ./docker/nginx.conf /etc/nginx/

CMD ["nginx", "-g", "daemon off;"]
