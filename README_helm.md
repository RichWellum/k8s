# Helm Help #
## References ##

[Using Helm](https://docs.helm.sh/using_helm/)

## THREE BIG CONCEPTS ##

A Chart is a Helm package. It contains all of the resource definitions
necessary to run an application, tool, or service inside of a
Kubernetes cluster. Think of it like the Kubernetes equivalent of a
Homebrew formula, an Apt dpkg, or a Yum RPM file.

A Repository is the place where charts can be collected and
shared. It’s like Perl’s CPAN archive or the Fedora Package Database,
but for Kubernetes packages.

A Release is an instance of a chart running in a Kubernetes
cluster. One chart can often be installed many times into the same
cluster. And each time it is installed, a new release is
created. Consider a MySQL chart. If you want two databases running in
your cluster, you can install that chart twice. Each one will have its
own release, which will in turn have its own release name.

With these concepts in mind, we can now explain Helm like this:

Helm installs charts into Kubernetes, creating a new release for each
installation. And to find new charts, you can search Helm chart
repositories.

## Commands ##

### ‘HELM SEARCH’: FINDING CHARTS ###
You can see which charts are available by running: $ helm search

With no filter, helm search shows you all of the available charts. You
can narrow down your results by searching with a filter:

    $ helm search mysql

### ‘HELM INSPECT’: showing package description ###

Use 'helm inspect chart' to see a chart's package description:

    $ helm inspect stable/mariadb
    Fetched stable/mariadb to mariadb-0.5.1.tgz
    description: Chart for MariaDB
    engine: gotpl
    home: https://mariadb.org
    keywords:
    - mariadb
    - mysql
    - database
    - sql
    ...

### ‘HELM INSTALL’: INSTALLING A PACKAGE ###
To install a new package, use the helm install command. At its
simplest, it takes only one argument: The name of the chart.


    $ helm install stable/mariadb
    Fetched stable/mariadb-0.3.0 to /Users/mattbutcher/Code/Go/src/k8s.io/helm/mariadb-0.3.0.tgz
    happy-panda
    Last Deployed: Wed Sep 28 12:32:28 2016
    Namespace: default
    Status: DEPLOYED

    Resources:
    ==> extensions/Deployment
    NAME                     DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
    happy-panda-mariadb   1         0         0            0           1s

    ==> v1/Secret
    NAME                     TYPE      DATA      AGE
    happy-panda-mariadb   Opaque    2         1s

    ==> v1/Service
    NAME                     CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE
    happy-panda-mariadb   10.0.0.70    <none>        3306/TCP   1s


    Notes:
    MariaDB can be accessed via port 3306 on the following DNS name from within your cluster:
    happy-panda-mariadb.default.svc.cluster.local

Now the mariadb chart is installed. Note that installing a chart
creates a new release object. The release above is named
happy-panda. (If you want to use your own release name, simply use the
--name flag on helm install.)

During installation, the helm client will print useful information
about which resources were created, what the state of the release is,
and also whether there are additional configuration steps you can or
should take.

Helm does not wait until all of the resources are running before it
exits. Many charts require Docker images that are over 600M in size,
and may take a long time to install into the cluster.

### 'HELM STATUS': KEEP TRACK OF A RELEASE STATE ###
To keep track of a release’s state, or to re-read configuration
information, you can use helm status:

    $ helm status happy-panda
    Last Deployed: Wed Sep 28 12:32:28 2016
    Namespace: default
    Status: DEPLOYED

### Customizign a Chart before Deployment ###
Installing the way we have here will only use the default
configuration options for this chart. Many times, you will want to
customize the chart to use your preferred configuration.

#### 'HELM INSPECT VALUES': To see what options are configurable on a chart ####

    $ helm inspect values stable/chaoskube
    # container name
    name: chaoskube

    # docker image
    image: quay.io/linki/chaoskube

    # docker image tag
    imageTag: v0.8.0

    # number of replicas to run
    replicas: 1

    # interval between pod terminations
    interval: 10m

    # label selector to filter pods by, e.g. app=foo,stage!=prod
    labels:

    # annotation selector to filter pods by, e.g. chaos.alpha.kubernetes.io/enabled=true
    annotations:

    # namespace selector to filter pods by, e.g. '!kube-system,!production' (use quotes)
    namespaces:

    # don't kill pods, only log what would have been done
    dryRun: true

#### Override settings with yaml file ####

You can then override any of these above settings in a YAML formatted
file, and then pass that file during installation.

    echo '{dryRun: False}' > config.yaml
    $ helm install -f config.yaml stable/chaoskube

#### Override settings with overrides ####
    $ helm install --set dryRun=False

### More Install Methods ###
The helm install command can install from several sources:

A chart repository (as we’ve seen above) A local chart archive (helm
install foo-0.1.1.tgz) An unpacked chart directory (helm install
path/to/foo) A full URL (helm install
https://example.com/charts/foo-1.2.3.tgz)

### ‘HELM UPGRADE’ AND ‘HELM ROLLBACK’: UPGRADING A RELEASE, AND
    RECOVERING ON FAILURE ###


When a new version of a chart is released, or when you want to change
the configuration of your release, you can use the helm upgrade
command.

An upgrade takes an existing release and upgrades it according to the
information you provide. Because Kubernetes charts can be large and
complex, Helm tries to perform the least invasive upgrade. It will
only update things that have changed since the last release.

    $ helm upgrade -f panda.yaml happy-panda stable/mariadb
    Fetched stable/mariadb-0.3.0.tgz to /Users/mattbutcher/Code/Go/src/k8s.io/helm/mariadb-0.3.0.tgz
    happy-panda has been upgraded. Happy Helming!
    Last Deployed: Wed Sep 28 12:47:54 2016
    Namespace: default
    Status: DEPLOYED
    ...

In the above case, the happy-panda release is upgraded with the same
chart, but with a new YAML file:

mariadbUser: user1 We can use helm get values to see whether that new
setting took effect.

#### 'HELM GET VALUES': See running settings ####

    $ helm get values happy-panda
    mariadbUser: user1

The helm get command is a useful tool for looking at a release in the
cluster. And as we can see above, it shows that our new values from
panda.yaml were deployed to the cluster.

#### 'HELM ROLLBACK': Rollback to a previous version ####
Now, if something does not go as planned during a release, it is easy
to roll back to a previous release using helm rollback [RELEASE]
[REVISION].

    $ helm rollback happy-panda 1

The above rolls back our happy-panda to its very first release
version. A release version is an incremental revision. Every time an
install, upgrade, or rollback happens, the revision number is
incremented by 1. The first revision number is always 1. And we can
use helm history [RELEASE] to see revision numbers for a certain
release.

### ‘HELM DELETE’: DELETING A RELEASE ###
When it is time to uninstall or delete a release from the cluster, use
the helm delete command:

    $ helm delete happy-panda

This will remove the release from the cluster. You can see all of your
currently deployed releases with the helm list command:

### ‘HELM LIST’: List all deployed releases ###

    $ helm list
    NAME           	VERSION	UPDATED                        	STATUS         	CHART
    inky-cat       	1      	Wed Sep 28 12:59:46 2016       	DEPLOYED       	alpine-0.1.0

From the output above, we can see that the happy-panda release was
deleted.

However, Helm always keeps records of what releases happened. Need to
see the deleted releases?  $ helm list --deleted shows those, and $
helm list --all shows all of the releases (deleted and currently
deployed, as well as releases that failed):

### ‘HELM REPO’: WORKING WITH REPOSITORIES ###

So far, we’ve been installing charts only from the stable
repository. But you can configure helm to use other repositories. Helm
provides several repository tools under the helm repo command.

#### 'HELM REPO LIST': See which repos are configured ####

You can see which repositories are configured using helm repo list:

    $ helm repo list NAME URL stable
    https://kubernetes-charts.storage.googleapis.com local
    http://localhost:8879/charts mumoshu https://mumoshu.github.io/charts

#### 'HELM REPO ADD': See which repos can be added ####

And new repositories can be added with helm repo add:

    $ helm repo add dev https://example.com/dev-charts

#### 'HELM REPO UPDATE: Make sure helm client is up-to-date ####

Because chart repositories change frequently, at any point you can
make sure your Helm client is up to date by running helm repo update.

    $ helm repo update

### CREATING YOUR OWN CHARTS ###

#### 'HELM CREATE': Quickly create own chart ####
The Chart Development Guide explains how to develop your own
charts. But you can get started quickly by using the helm create
command:

    $ helm create deis-workflow

Now there is a chart in ./deis-workflow. You can edit it and create
your own templates.

#### 'HELM LINT': Syntax check ####

As you edit your chart, you can validate that it is well-formatted by
running: $ helm lint.

#### 'HELM PACKAGE': package new chart ####
When it’s time to package the chart up for distribution, you can run
the helm package command:

    $ helm package deis-workflow
    deis-workflow-0.1.0.tgz

And that chart can now easily be installed by helm install:

    $ helm install ./deis-workflow-0.1.0.tgz
