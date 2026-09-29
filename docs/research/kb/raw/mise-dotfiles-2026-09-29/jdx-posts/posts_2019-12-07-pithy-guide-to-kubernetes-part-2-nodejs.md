[Skip to content](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/#main)

On this page

If you haven’t done [Part 1](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1) you’ll need to start there.

In Part 1 we setup Minikube and added an Ingress, Service, and Deployment to the k8s cluster. Now
we’ll finish that work by giving the Deployment an image to load.

The full example code is available on [GitHub](https://github.com/jdx/pithy-nodejs).

## Build the Node API [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/\#build-the-node-api)

First create a `package.json` file for our dependencies and add express to the app:

```sh
$ mkdir api
$ cd api
$ echo '{}' > package.json
$ npm i express
```

Now create a simple express JSON API:

`api/app.js`

```javascript
const express = require("express");
const app = express();

const port = "8000";

app.get("/api/info", (req, res) => {
  res.send({ status: "ok" });
});

app.listen(port, () => {
  console.log(`Listening on port :${port}`);
});
```

Make sure it works ok by starting it locally and hitting the API:

```sh
$ node api/app.js
Listening on port :8000

$ curl -i localhost:8000/api/info
HTTP/1.1 200 OK
X-Powered-By: Express
Content-Type: application/json; charset=utf-8
Content-Length: 15

{"status":"ok"}
```

## Dockerize Node.js API [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/\#dockerize-nodejs-api)

Now we’ll package the API up so we can let k8s pick it up. Create the API Dockerfile:

`./api/Dockerfile`

```dockerfile
FROM node:12-alpine

WORKDIR ~/src/pithy-nodejs/api
ADD api .
RUN npm i
EXPOSE 8000
ENTRYPOINT node app.js
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
Sending build context to Docker daemon  2.042MB
Step 1/6 : FROM node:12-alpine
 ---> 3fb8a14691d9
Step 2/6 : WORKDIR ~/src/pithy-nodejs/api
 ---> Using cache
 ---> abe40cb4ccfa
Step 3/6 : ADD api .
 ---> c2e704826546
Step 4/6 : RUN npm i
 ---> Running in c9ef87efbd10

audited 126 packages in 0.549s
found 0 vulnerabilities

Removing intermediate container c9ef87efbd10
 ---> 01834c1cd5c2
Step 5/6 : EXPOSE 8000
 ---> Running in aac3df1f7625
Removing intermediate container aac3df1f7625
 ---> dfc28b5108a2
Step 6/6 : ENTRYPOINT node app.js
 ---> Running in 62cb15cb3f96
Removing intermediate container 62cb15cb3f96
 ---> ad844e693b7d
Successfully built ad844e693b7d
Successfully tagged pithy-api-img:v1

$ docker run -p 8000:8000 pithy-api-img:v1
Listening on port :8000
http GET /api/info

$ curl -i minikube:8000/api/info
HTTP/1.1 200 OK
X-Powered-By: Express
Content-Type: application/json; charset=utf-8
Content-Length: 15

{"status":"ok"}
```

## Check if Pod is Running [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/\#check-if-pod-is-running)

Our cluster should be up now as we’ve added that missing image. We can see the app is up in the
logs:

```sh
$ kubectl logs -l app=pithy-api
Listening on port :8000
```

If it’s not running you can try deleting the pod:

```sh
$ kubectl delete pod -l app=pithy-api
pod "pithy-api-deployment-7dc4f5676d-crtlj" deleted
```

There isn’t any need to start a new pod because that’s all managed by the Deployment—which has not
changed and still requires 1 replica pod. Once k8s notices that it is missing the deleted pod, it
starts it.

If things still aren’t working try deleting the ingress, service, and deployment and applying the
config again. Check the dashboard too to see if there are any obvious errors you can find.

## Scaling up [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/\#scaling-up)

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
Listening on :8000
Listening on :8000
Listening on :8000
```

Let’s say we want to know which host each of these was running on though. The hostname is provided
in an environment variable so it’s as easy as changing the log output in the app code to include
the hostname:

`api/app.js`

```javascript
app.listen(port, () => {
  const hostname = process.env.HOSTNAME;
  console.log(`${hostname} Listening on port :${port}`);
});
```

Now we’ll rebuild the container, and to trigger a redeploy we’ll delete the pods and allow them to
be recreated with the new image. Then we’ll see that the hostname has been added to the logs:

```sh
$ docker build . -f api/Dockerfile -t pithy-api-img:v1
Sending build context to Docker daemon  2.042MB
Step 1/6 : FROM node:12-alpine
 ---> 3fb8a14691d9
Step 2/6 : WORKDIR ~/src/pithy-nodejs/api
 ---> Using cache
 ---> abe40cb4ccfa
Step 3/6 : ADD api .
 ---> 933439405b70
Step 4/6 : RUN npm i
 ---> Running in 6f830dce6ddc

audited 126 packages in 0.567s
found 0 vulnerabilities

Removing intermediate container 6f830dce6ddc
 ---> 15a95f1a6f0a
Step 5/6 : EXPOSE 8000
 ---> Running in 52af2c83c1c7
Removing intermediate container 52af2c83c1c7
 ---> 520004ac92b9
Step 6/6 : ENTRYPOINT node app.js
 ---> Running in 6911881ddb00
Removing intermediate container 6911881ddb00
 ---> 0ffa7eabfefc
Successfully built 0ffa7eabfefc
Successfully tagged pithy-api-img:v1

$ kubectl logs -l app=pithy-api
pithy-api-deployment-7dc4f5676d-9q87h Listening on port :8000
pithy-api-deployment-7dc4f5676d-ch8qq Listening on port :8000
pithy-api-deployment-7dc4f5676d-pm9zz Listening on port :8000

$ kubectl logs -l app=pithy-api
pithy-api-deployment-7dc4f5676d-ftv4m Listening on port :8000
pithy-api-deployment-7dc4f5676d-krm2c Listening on port :8000
pithy-api-deployment-7dc4f5676d-tdzvm Listening on port :8000
```

## Next Steps [\#](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/\#next-steps)

Congrats! You’ve just built a Kubernetes cluster! Here are some suggestions of exercises you can do
to continue learning:

- Migrate from Minikube to a cloud provider.
- Add a Makefile or other build system to make deploys easier.
- Instead of tagging releases with `:v1`, see if you can tag it based on git sha.
- Try another API to the cluster routed to a different pathname in the Ingress.
- Enable SSL termination at the Ingress.