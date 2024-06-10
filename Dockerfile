FROM python:3.8-alpine
# FROM alpine

RUN pip3 install requests

COPY *.py /root/
COPY LICENSE /root/LICENSE
COPY README.md /root/README.md

# RUN echo '@community http://dl-cdn.alpinelinux.org/alpine/edge/community' >> /etc/apk/repositories && \
# 	echo '@edge http://dl-cdn.alpinelinux.org/alpine/edge/main' >> /etc/apk/repositories && \
# 	apk add --upgrade --no-cache --update ca-certificates wget git curl openssh tar gzip python3 apk-tools@edge && \
# 	apk upgrade --update --no-cache

RUN mkdir /logs

WORKDIR /root

ARG CRON_SCHEDULE="*/30 * * * *"
RUN echo "$(crontab -l 2>&1; echo "${CRON_SCHEDULE} /root/dns.tcl")" | crontab -

CMD ["crond", "-f", "2>&1"]
