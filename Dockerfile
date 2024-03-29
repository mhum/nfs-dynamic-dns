FROM alpine:latest

COPY *.tcl /root/
COPY packages/* /root/packages/
COPY LICENSE /root/LICENSE
COPY README.md /root/README.md

RUN apk add tcl tcl-tls

RUN echo '@community http://dl-cdn.alpinelinux.org/alpine/edge/community' >> /etc/apk/repositories && \
	echo '@edge http://dl-cdn.alpinelinux.org/alpine/edge/main' >> /etc/apk/repositories && \
	apk add --upgrade --no-cache --update ca-certificates wget git curl openssh tar gzip apk-tools@edge && \
	apk upgrade --update --no-cache

# https://github.com/gjrtimmer/docker-alpine-tcl/blob/master/Dockerfile#L38
RUN curl -sSL https://github.com/tcltk/tcllib/archive/release.tar.gz | tar -xz -C /tmp && \
	tclsh /tmp/tcllib-release/installer.tcl -no-html -no-nroff -no-examples -no-gui -no-apps -no-wait -pkg-path /usr/lib/tcllib && \
	rm -rf /tmp/tcllib*

RUN mkdir /logs

WORKDIR /root

ARG CRON_SCHEDULE="*/30 * * * *"
RUN echo "$(crontab -l 2>&1; echo "${CRON_SCHEDULE} /root/dns.tcl")" | crontab -

CMD ["crond", "-f", "2>&1"]
