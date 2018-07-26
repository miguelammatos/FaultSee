FROM golang as builder

WORKDIR /go_dependencies

# <- COPY go.mod and go.sum files to the workspace
COPY go.mod .
COPY go.sum .

# Get dependancies - will also be cached if we won't change mod/sum
RUN go mod download


# RUN go get -d -v github.com/docker/go-plugins-helpers/ipam
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o app .

FROM scratch
COPY --from=builder /app/app .
EXPOSE 7000
ENTRYPOINT ["/app"]
