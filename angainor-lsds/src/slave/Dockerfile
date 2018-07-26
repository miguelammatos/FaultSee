FROM golang:1.12 as builder

WORKDIR /go_dependencies

# <- COPY go.mod and go.sum files to the workspace
COPY go.mod .
COPY go.sum .

# Get dependancies - will also be cached if we won't change mod/sum
RUN go mod download

#legacy
# RUN go get -d -v github.com/docker/docker/client
# RUN go get -d -v golang.org/x/sys/unix
# RUN go get -d -v github.com/shirou/gopsutil
# RUN go get -d -v github.com/kr/pretty
# RUN go get -d -v gopkg.in/yaml.v2
# # Fix "client version" error
# RUN cd /go/src/github.com/docker/docker && git checkout 967224c254884d6659ad7ec66bdd9da1b4c7d49f

WORKDIR /app
COPY . /app
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o app .

FROM scratch
WORKDIR /app
COPY --from=builder /app/app .
EXPOSE 7000
CMD ["./app"]
