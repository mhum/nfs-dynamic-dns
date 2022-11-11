FROM alpine:latest

# docker run --rm -it -v /home/ace/Scripts/nfs-dynamic-dns:/root 

COPY *.tcl /root/
COPY packages/* /root/packages/
COPY LICENSE /root/LICENSE
COPY README.md /root/README.md

RUN apk add tcl
RUN mkdir /logs
WORKDIR /root
RUN echo $(crontab -l ; echo "*/5     *       *       *       *       /root/dns.tcl 2>&1 > /logs/$(date -Iseconds).log") | crontab -
ENTRYPOINT ["crond", "-f"]