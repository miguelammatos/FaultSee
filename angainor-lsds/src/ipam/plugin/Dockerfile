FROM golang as builder
# RUN $GOPATH GOPATH=/go
# RUN echo $(pwd) pwd=/go
WORKDIR /go_dependencies

# <- COPY go.mod and go.sum files to the workspace
COPY go.mod .
COPY go.sum .

# Get dependancies - will also be cached if we won't change mod/sum
RUN go mod download


# RUN go get -d -v github.com/docker/go-plugins-helpers/ipam


# COPY the source code as the last step
# WORKDIR src/github.com/docker/go-plugins-helpers/ipam
# supose tag v0.0.2 is correct version
# RUN pwd
# RUN ls -l
# RUN git checkout tags/v0.3.0
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o app .

FROM scratch
COPY --from=builder /app/app .
ENTRYPOINT ["/app"]
