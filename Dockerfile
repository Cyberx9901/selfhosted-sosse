FROM biolds/sosse:pip-base
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN mkdir /root/sosse
WORKDIR /root/sosse
ADD requirements.txt .
ADD pyproject.toml .
ADD MANIFEST.in .
ADD se/ se/
ADD sosse/ sosse/
RUN pip install ./ && pip install uwsgi && pip cache purge
ADD debian/sosse.conf /etc/nginx/sites-enabled/default
RUN mkdir -p /etc/sosse/ /etc/sosse_src/ /var/log/sosse /var/log/uwsgi
RUN sosse-admin default_conf | sed -e 's/^#db_pass.*/db_pass=sosse/' -e 's/^#\(browser_options=.*\)$/\1 --no-sandbox/' > /etc/sosse_src/sosse.conf
ADD debian/uwsgi.* /etc/sosse_src/
RUN chown -R root:www-data /etc/sosse /etc/sosse_src && chmod 750 /etc/sosse_src/ && chmod 640 /etc/sosse_src/*

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER sosse WITH PASSWORD 'sosse';" && \
    createdb -O sosse sosse

USER root
RUN echo '#!/bin/bash -x \n \
/etc/init.d/postgresql start \n \
test -e /etc/sosse/sosse.conf || (cp -p /etc/sosse_src/* /etc/sosse/) \n \
mkdir -p /run/sosse \n \
touch /var/log/sosse/{debug.log,main.log,crawler.log,uwsgi.log,webserver.log} \n \
chown -R www-data:www-data /run/sosse /var/log/sosse/ \n \
sosse-admin migrate \n \
sosse-admin collectstatic --noinput \n \
sosse-admin update_se \n \
sosse-admin default_admin \n \
/usr/local/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini --logto /var/log/sosse/uwsgi.log & \n \
/etc/init.d/nginx start \n \
sosse-admin crawl & \n \
tail -F /var/log/sosse/crawler.log' > /run.sh ; chmod +x /run.sh
CMD /run.sh
