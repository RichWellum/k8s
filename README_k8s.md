# Basic Description #

## Kubeadm ##

  * kubeadm is a tool built to provide kubeadm init and kubeadm join
    as best-practice “fast paths” for creating Kubernetes clusters.

  * kubeadm performs the actions necessary to get a minimum viable
    cluster up and running. By design, it cares only about
    bootstrapping, not about provisioning machines. Likewise,
    installing various nice-to-have addons, like the Kubernetes
    Dashboard, monitoring solutions, and cloud-specific addons, is not
    in scope.

  * Instead, expectation is that more tailored tooling to be built on
    top of kubeadm, and ideally, using kubeadm as the basis of all
    deployments will make it easier to create conformant clusters.


## k8s.py ##


  * A lot of the tools for deploying Kubernetes for simple operations
    are based around 'development' or non-production tools, like
    minikube for example. But in my opinion, Kubernetes is easy enough
    and stable enough to be instantiated without dedicated development
    tools that then require the user to pivot to using
    production-grade tools when they decide on their next step. A lot
    of the development tools, are designed to provide an isolated
    environment, that guarantees the user an environment that
    Kubernetes will always come up.



  * So I wrote k8s.py, to handle different user environments, install
 needed software, bring up Kubernetes, network at the SDN layer and
 install Tiller so that the cluster is up, running and ready to deploy
 helm  charts, and most importantly is production-ready.

### Disadvantages of k8s.py ###


  * k8s.py is written in python. At the time of initial conception, it
    was a tool to deploy OpenStack on top of Kubernetes and a lot of
    options were needed to determine what was going to be deployed,
    and a lot of versioning was also needed as certain combinations of
    versions of Docker, Kubernetes, OpenStack etc were required for
    successful operation. Python has strong input language and
    provided that functionality. Python is functional in nature, while
    most of the DevOps world is moving towards declarative languages
    like yaml and ansible - this means any changes to the cluster that
    k8s.py brings up has to be coded in the tool, instead of changed
    in a YAML values file.


  * Go would have been the native language to use - as it's symbiotic
    with Kubernetes and Helm, cross-compiled and very fast.


### Advantages of k8s.py ###


  * There are not many production capable tools that simply bring up a
    Kubernetes cluster without overlaying it with a single vendor's
    needs or biasedness. The only choice taken here is to use Weave as
    the CNI/SDN.


  * It runs on a VM, and installs the tools needed to run.

  * It works on Ubuntu, Centos and Flatcar.

  * Includes a clean up option, various verbose modes.

### Prerequisites ###

#### The host machine must satisfy the following minimum requirements: ####

- 1 network interfaces
- 2GB min, 4GB+ preferred RAM
- 20G min, 40GB+ preferred disk space
- 2 CPU's Min, 4+ preferred CPU's
- Root access to the deployment host machine

#### Add user (centos/ubuntu) ####

- Create an admin user - don't run from root
- Disable timeouts

##### Centos #####

    adduser stack
    passwd stack
    usermod -aG wheel stack


##### Ubuntu #####

    adduser stack
    usermod -aG sudo stack


##### Both 'visudo': #####

    stack ALL=(ALL) NOPASSWD: ALL
    Defaults timestamp_timeout=-1
