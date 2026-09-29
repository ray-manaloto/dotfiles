[Skip to content](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/#main)

On this page

If you haven’t done [Part 1](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1) you’ll need to start there.

In Part 1 we setup Minikube and added an Ingress, Service, and Deployment to the k8s cluster. Now
we’ll finish that work by giving the Deployment an image to load.

The full example code is available on [GitHub](https://github.com/jdx/pithy-go).

## Build the Go API [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/\#build-the-go-api)

First initialize this directory as a Go module: \[optional, but recommended\]

```sh
$ go mod init
```

Now create a simple Go JSON API:

`api/main.go`

```go
package main

import (
	"encoding/json"
	"log"
	"net/http"
)

const PORT = ":8000"

func main() {
	http.HandleFunc("/api/info", Info)
	log.Printf("listening on %s\n", PORT)
	if err := http.ListenAndServe(PORT, nil); err != nil {
		log.Fatal(err)
	}
}

func Info(w http.ResponseWriter, r *http.Request) {
	type Response struct{ Status string }
	log.Printf("http %s\n", r.RequestURI)
	sendJSON(w, Response{Status: "OK"})
}

func sendJSON(w http.ResponseWriter, o interface{}) {
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(o); err != nil {
		log.Print(err)
	}
}
```

Make sure it works ok by starting it locally and hitting the API:

```sh
$ go run ./api
2019/12/08 03:34:50 listening on :8000

$ curl -i localhost:8000/api/info
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 16

{"Status":"OK"}
```

## Dockerize Go API [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/\#dockerize-go-api)

Now we’ll package the API up so we can let k8s pick it up. Create the API Dockerfile[1](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/#fn:1):

`./api/Dockerfile`

```dockerfile
FROM golang:1.13-alpine

WORKDIR ~/src/pithy-go
ADD go.mod go.mod
ADD api api
RUN go build -o ./bin/api ./api
EXPOSE 8000
ENTRYPOINT ./bin/api
```

Before we build the image, we need to point docker to use the minikube registry instead of the
local one so the image we build will be availble to k8s:

```sh
$ eval $(minikube docker-env)
```

_**Note:** This just sets local env vars so will only affect the current shell session._

Build and run the Docker container outside k8s first to make sure it is working:

```sh
$ docker build . -f api/Dockerfile -t pithy-api-img:v1
$ docker run -p 8000:8000 pithy-api-img:v1
$ curl -i minikube:8000/api/info
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 16

{"Status":"OK"}
```

## Check if Pod is Running [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/\#check-if-pod-is-running)

Our cluster should be up now as we’ve added that missing image. We can see the app is up in the
logs:

```sh
$ kubectl logs -l app=pithy-api
2019/12/08 03:34:50 listening on :8000
```

If it’s not running you can try deleting the pod:

```sh
$ kubectl delete pod -l app=pithy-api
pod "pithy-api-deployment-7dc4f5676d-6nj4w" deleted
```

There isn’t any need to start a new pod because that’s all managed by the Deployment—which has not
changed and still requires 1 replica pod. Once k8s notices that it is missing the deleted pod, it
starts it.

If things still aren’t working try deleting the ingress, service, and deployment and applying the
config again. Check the dashboard too to see if there are any obvious errors you can find.

## Scaling up [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/\#scaling-up)

If we want to increase the number of pods running our API, all we need to do is set the # of
replicas we want and apply the config. Try updating it to 3 instead of 1:

`k8s/api.yml`

```yaml
apiVersion: 'apps/v1'
kind: 'Deployment'
metadata:
  name: 'pithy-api-deployment'
  labels:
    app: 'pithy-api'
spec:
  replicas: 3
  ...
```

Now apply the config and check the logs for 3 listening messages:

```sh
$ kubectl apply -f k8s/api.yml
service/pithy-api-svc unchanged
deployment.apps/pithy-api-deployment configured

$ kubectl logs -l app=pithy-api
2019/12/08 03:45:44 listening on :8000
2019/12/08 03:45:44 listening on :8000
2019/12/08 03:45:44 listening on :8000
```

Let’s say we want to know which host each of these was running on though. The hostname is provided
in an environment variable so it’s as easy as changing the log output in the Go code to include the
hostname:

`api/main.go`

```go
func main() {
	http.HandleFunc("/api/info", Info)
	hostname := os.Getenv("HOSTNAME")
	log.Printf("%s listening on %s\n", hostname, PORT)
	if err := http.ListenAndServe(PORT, nil); err != nil {
		log.Fatal(err)
	}
}
```

Now we’ll rebuild the container, and to trigger a redeploy we’ll delete the pods and allow them to
be recreated with the new image. Then we’ll see that the hostname has been added to the logs:

```sh
$ docker build . -f api/Dockerfile -t pithy-api-img:v1
Sending build context to Docker daemon  89.09kB
Step 1/7 : FROM golang:1.13-alpine
 ---> 69cf534c966a
Step 2/7 : WORKDIR ~/src/pithy-go
 ---> Using cache
 ---> 598d3fafce6f
Step 3/7 : ADD go.mod go.mod
 ---> Using cache
 ---> d975f73d965e
Step 4/7 : ADD api api
 ---> Using cache
 ---> 6acf7766a2f7
Step 5/7 : RUN go build -o ./bin/api ./api
 ---> Using cache
 ---> 87bda87de0ef
Step 6/7 : EXPOSE 8000
 ---> Using cache
 ---> 8ec40d3c1f7b
Step 7/7 : ENTRYPOINT ./bin/api
 ---> Using cache
 ---> fb3c2809cd01
Successfully built fb3c2809cd01
Successfully tagged pithy-api-img:v1

$ kubectl delete pod -l app=pithy-api
pod "pithy-api-deployment-7dc4f5676d-f8sk7" deleted
pod "pithy-api-deployment-7dc4f5676d-sbrrz" deleted
pod "pithy-api-deployment-7dc4f5676d-x2xpw" deleted

$ kubectl logs -l app=pithy-api
2019/12/08 03:58:39 pithy-api-deployment-7dc4f5676d-ckbw9 listening on :8000
2019/12/08 03:58:39 pithy-api-deployment-7dc4f5676d-cqjbj listening on :8000
2019/12/08 03:58:39 pithy-api-deployment-7dc4f5676d-qzp6f listening on :8000
```

## Next Steps [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/\#next-steps)

Congrats! You’ve just built a Kubernetes cluster! Here are some suggestions of exercises you can do
to continue learning:

- Migrate from Minikube to a cloud provider.
- Add a Makefile or other build system to make deploys easier.
- Instead of tagging releases with `:v1`, see if you can tag it based on git sha.
- Try another API to the cluster routed to a different pathname in the Ingress.
- Enable SSL termination at the Ingress.

## Footnotes [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/\#footnotes)

* * *

1. Alternatively you could build the app locally and copy it into the container. This makes for
a much smaller base image since it doesn’t require the Go buildchain or even the source
files. However it also means you lose the benefit of having a consistent build environment
and you won’t be able to use this image for CI runs. For these reasons, I would keep with a
single Dockerfile for everything in the API. [↩︎](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/#fnref:1)