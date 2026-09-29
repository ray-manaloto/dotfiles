[Skip to content](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#main)

On this page

This is a concise, opinionated guide to Kubernetes. I’m assuming you already know how to build
software and are just looking to get started with Kubernetes. This is a 2-parter: the first is
language-agnostic and the second is for a particular language. I have Go and Node right now.

Assume we want to build a JSON web server managed by Kubernetes. At the end of this guide, we will
be able to do this:

```sh
$ curl -i http://minikube/api/info
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 16

{"Status":"OK"}
```

_**Note**: `minikube` will be mapped in `/etc/hosts` to our local Kubernetes cluster_

If you’re looking for something comprehensive, the [official docs](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/kubernetes.io) will be much better. If you’re
new to software, this also isn’t the article for you, but Kubernetes is probably too advanced
anyways.

## Expectations [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#expectations)

- You are an experienced software engineer.
- If I asked you to build me a docker container of a hello world node.js app you wouldn’t struggle.
- You have (at least) a vague idea of what Kubernetes is and why you might want to use it.
If you’re just able to mumble something about docker and/or orchestration that’s enough for now.

## Kubernetes Overview [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#kubernetes-overview)

_**Note:** Skip me if you already “get” kubernetes and you’re just looking to build something._

Quickly, let’s go over what Kubernetes (k8s) is:

- k8s manages Docker[1](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:1) containers in production. This is not for local development[2](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:2).
- For example: you give it some servers and tell it you want 10 app containers running:
  - k8s determines where to launch containers based on expected cpu/mem
  - k8s routes requests so that they can be reached from other containers or the outside world
- Apps are ephemeral and can be started/stopped at any time[3](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:3).
- Generally you use it with a provider such as AWS/GCP/Azure—though there is also some support for
on-prem.

It’s the [promise of Docker](https://www.docker.com/resources/what-container) finally fulfilled in production. SRE—or devops or just devs with their
ops-hats on—don’t have to manually stand up servers to put apps/services on. They just tell k8s
“I need this many pods” and it figures out where to put them. When you need to scale up you can
look at how much cpu/mem/disk you need over the entire system rather than individual services.

Most software teams are either migrating to it, investigating it, or trying to come up with
reasonable sounding arguments as to why they shouldn’t. It’s the gold standard right now for
architecture[4](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:4).

Also, if you’re considering microservices, k8s is basically a prerequisite. Otherwise you’ll lose
any potential gains of having smaller services due to increased ops work.

## Interacting with Kubernetes [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#interacting-with-kubernetes)

_**Note:** Skip me if you already know what `kubectl apply` is used for._

Developers (in my experience) need to know how they’ll interact with a system before they can even
begin to comprehend it—so we’ll start there. We use a CLI called [`kubectl`](https://kubernetes.io/docs/reference/kubectl/overview/) to interact with the
cluster. For managing the cluster itself we use minikube (or your provider’s console/CLI).

For example, if you want to add a machine to a GKE (k8s on GCP) cluster: use `gcloud`. If you need to connect
an API instance to a database, use `kubectl`. Both in this article and the real world
you’ll use `kubectl` much more. This is nice because you can take your knowledge of working with k8s from provider to
provider and work mostly the same way.

You might assume (and you would be right) that you use `kubectl` to add a new web API mapped to a
docker image. Something like the following to create one of these things:

```sh
$ kubectl create deployment hello-node --image=gcr.io/hello-minikube-zero-install/hello-node
```

In fact I stole this command from the [official getting started docs](https://kubernetes.io/docs/tutorials/hello-minikube/#create-a-deployment).
What those docs don’t even mention that is nobody[5](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:5) uses `kubectl` like this! There is a
much better way that everyone _does_ use that’s great for playing around _or_ for production
systems. It’s `kubectl apply`.

The issue with `kubectl create deployment` (or `kubectl create [ANYTHING]`) is you lose the paper
trail and it’s hard to remember how you did something. Instead we create/modify a yaml file and
_apply_ it to our system. If the yaml file has a new [object](https://kubernetes.io/docs/concepts/#kubernetes-objects) (in this case a Deployment), it will
create it. If it has changes and already exists, it will update it. The ideal way to modify a
production cluster would be to have your k8s files in a repo and apply them once they’ve been
reviewed and merged.

Even while we’re playing around in this article it’s good to use `kubectl apply` because it’s nice
to be able to blow away a cluster and rebuild it from the yaml configs on disk. Once we get started
building our cluster you’ll see these files in action.

## Anatomy of Kubernetes [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#anatomy-of-kubernetes)

We’ll build this outside-in[6](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:6). Let’s follow the lifecycle of our `curl minikube/api/info`
request:

1. Laptop calls `curl minikube/api/info`.
2. **ingress** accepts request and finds matching **service** in minikube cluster[7](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:7).
3. **service** finds a matching **pod** to for the incoming request.
4. **pod** takes the request, handles it, and responds back to `curl`.

TCP is the language spoken throughout. Aside from the Ingress (which is HTTP), k8s connects TCP
sockets from **ingress** → **service** → **pod**. Of course you can also go with UDP.

Let’s define these terms:

[**provider**](https://kubernetes.io/docs/concepts/cluster-administration/cloud-providers/)AWS/GCP/minikube[**cluster**](https://kubernetes.io/docs/concepts/)A set of compute boxes (e.g.: EC2) that are running k8s.[**ingress**](https://kubernetes.io/docs/concepts/services-networking/ingress/)maps connections _from the world to the cluster_. For minikube, the ingress is
nginx. For AWS it would be an Elastic Load Balancer (ELB). Think of it sitting outside
the cluster. It connects the world to services. Generally there will be 1 for an entire
cluster. Maybe more when there are multiple hostnames—though, certainly not
necessarily.[**service**](https://kubernetes.io/docs/concepts/services-networking/service/)maps connections _inside the cluster_ [8](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:8). (e.g.: Ingress to API, or API to database)[**pod**](https://kubernetes.io/docs/concepts/workloads/pods/pod/)a single, ephemeral[9](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:9) instance of a docker container running on a single instance. They can
die at any time.[**deployment**](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)defines how many pods of a certain type should be running at once. You won’t directly manage
pods, you’ll manage the deployment and k8s will automatically add/remove pods as
necessary.

## Walkthrough [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#walkthrough)

Now we’ll actually build this thing. Create a new directory for our project:

```sh
mkdir ~/src/pithy
cd ~/src/pithy
```

## Setup Cluster (minikube) [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#setup-cluster-minikube)

We need a kubernetes provider. There are lots of options. We could go straight to a
production-ready provider like GCP but it’s better to start with
[minikube](https://kubernetes.io/docs/tasks/tools/install-minikube/) [10](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:10). Go ahead and install it.
Then start it with `minikube start`.

Minikube gives itself an IP address but lets put it into `/etc/hosts` so we don’t have to
copy/paste it \[optional\]:

```sh
$ echo "$(minikube ip) minikube" | sudo tee -a /etc/hosts
```

## Add Ingress (nginx) [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#add-ingress-nginx)

First enable the ingress addon and verify it is running:

```sh
$ minikube addons enable ingress
$ kubectl get pods -n kube-system
NAME                                        READY     STATUS    RESTARTS   AGE
default-http-backend-59868b7dd6-xb8tq       1/1       Running   0          1m
kube-addon-manager-minikube                 1/1       Running   0          3m
kube-dns-6dcb57bcc8-n4xd4                   3/3       Running   0          2m
kubernetes-dashboard-5498ccf677-b8p5h       1/1       Running   0          2m
nginx-ingress-controller-5984b97644-rnkrg   1/1       Running   0          1m
storage-provisioner                         1/1       Running   0          2m
```

Now we need to configure the ingress for our system. Create the k8s config for it:

`k8s/ingress.yml`

```yaml
apiVersion: 'networking.k8s.io/v1beta1'
kind: 'Ingress'
metadata:
  name: 'pithy-ingress'
spec:
  backend:
    serviceName: 'pithy-api-svc' # to be added in the next step
    servicePort: 8000
```

Even though this points to a service we have yet to create (`pithy-api-svc`), apply it and
verify it was created successfully (note that the IP address might not show up right away):

```sh
$ kubectl apply -f k8s/ingress.yml
ingress.networking.k8s.io/pithy-ingress created
$ kubectl get ingress
NAME            HOSTS   ADDRESS        PORTS   AGE
pithy-ingress   *       192.168.64.5   80      24s
```

_**Tip:** You can also run `kubectl apply -f k8s` to apply all the yml files in the directory._

We can make a request to it with `curl -i minikube`. We’ll get a 503 error for not having our
service setup.

## Add Service/Deployment [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#add-servicedeployment)

Add the config for the API service and deployment:

`k8s/api.yml`[11](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:11)

```yaml
apiVersion: 'v1'
kind: 'Service'
metadata:
  name: 'pithy-api-svc'
spec:
  selector:
    app: 'pithy-api'
  ports:
    - port: 8000
---
apiVersion: 'apps/v1'
kind: 'Deployment'
metadata:
  name: 'pithy-api-deployment'
  labels:
    app: 'pithy-api'
spec:
  replicas: 1
  selector:
    matchLabels:
      app: 'pithy-api'
  template:
    metadata:
      labels:
        app: 'pithy-api'
    spec:
      containers:
      - name: 'pithy-api-img'
        image: 'pithy-api-img:v1' # we will build this in part 2
        ports:
          - containerPort: 8000
```

Most of this (the `app: 'pithy-api'` business) is so the service and deployment to track their
pods. You can have arbitrary labels to do this, we just use `app` per convention.

Then apply it:

```sh
$ kubectl apply -f k8s/api.yml
service/pithy-api-svc created
deployment.apps/pithy-api-deployment created
```

After a few seconds check the deployment logs, we expect to see an error stating it can’t find
the `pithy-api-img` image (because we haven’t built it yet):

```sh
$ kubectl logs -l app=pithy-api
Error from server (BadRequest): container "pithy-api-img" in pod "pithy-api-deployment-5f78b5f99d-p28q9" is waiting to start: image can't be pulled
```

There is also a dashboard feature we can use to view the status of the cluster. This is
particularly useful to discover functionality before you learn `kubectl`. Start it with:

```sh
$ minikube dashboard
```

In this instance, we can see this deployment is failing as expected:

![failing deployment in dashboard](https://jdx.dev/images/2019-12-07-pithy-kubernetes/failed-deployment.png)

## Build the API [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#build-the-api)

What’s missing is that `pithy-api:v1` Docker container. We just need to build a container that
will listen on that port.

We’ll save that for Part 2 as you’ll need to pick a language you want to work with. If I don’t have
your favorite, just pick one as the bulk of this stuff has very little to do with language.

- [Go API](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/)
- [Node API](https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/)

## Footnotes [\#](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/\#footnotes)

* * *

01. It can be other types of containers but let’s just concern ourselves with Docker. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:1)

02. There are certainly people that use k8s in dev, and projects for this purpose. It might
    sound appealing to be able to have that kind of dev/prod parity, but I’ve tried it and found
    it to be too complex and slow. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:2)

03. You can attach volumes for databases/etc [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:3)

04. This is a _how_ not a _why_ article. Do your own research to determine if k8s is right for
    your team. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:4)

05. Nobody I’ve seen at least. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:5)

06. We go outside-in because it’s a lot easier to understand a system by following the inputs to
    the outputs rather than starting in the middle. The downside is that it’ll be harder to get
    anything running since we’ll be missing components until the end. This isn’t how you would
    develop a real app. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:6)

07. You don’t have to use an Ingress to expose your service to the outside world. If you set the
    service type to [`LoadBalancer`](https://kubernetes.io/docs/tasks/access-application-cluster/create-external-load-balancer/).
    You can expose the service on a public IP address. You’ll save an extra hop and have a
    simpler architecture by doing this (especially with minikube), however services are _only_
    TCP/UDP, so you’ll miss out on HTTP routing, SSL termination, and lots of other features.
    It’s just TCP/UDP out to the world. If you’re not sure, use Ingress. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:7)

08. [As mentioned in 7](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fn:7), it is possible to expose services to the internet. It’s much
    more common to have an ingress though. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:8)

09. Pods can have [Volumes](https://kubernetes.io/docs/concepts/storage/volumes/) attached to be less ephemeral
    (for databases, your services should not have state). [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:9)

10. Minikube is built by the k8s team for this purpose—setting up basic clusters that eventually
    will go on to be hosted on a provider. It’s a lot faster than using a provider and the
    exercise of migrating this from minikube to GCP (or whatever) is helpful for you to
    understand where k8s ends and where your provider begins. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:10)

11. You can put the service and deployment into separate files if you prefer. [↩︎](https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/#fnref:11)