FROM swaggerapi/swagger-ui:v3.20.8

COPY ./docker/nginx.conf /etc/nginx/

CMD ["sh", "/usr/share/nginx/run.sh"]
