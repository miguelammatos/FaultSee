FROM alpine:3.10
RUN apk update
RUN apk add openntpd

ADD ntpd.conf /etc/ntpd.conf

ENTRYPOINT ["ntpd"]
CMD ["-f", "/etc/ntpd.conf", "-s"]
