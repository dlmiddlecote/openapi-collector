#!/bin/bash
echo "Start nginx"
nginx -g 'daemon off;' & 2>&1

echo "Wait until conf dir exists..."
while [ ! -d /etc/nginx/conf.d ]
do
  sleep 2
done

while true
do
        inotifywait --exclude .swp -e create -e modify -e delete -e move  /etc/nginx/conf.d
        # Check NGINX Configuration Test
        # Only Reload NGINX If NGINX Configuration Test Pass
        nginx -t
        if [ $? -eq 0 ]
        then
                echo "Reloading Nginx Configuration"
                service nginx reload
        fi
done
