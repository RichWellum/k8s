# kube-cluster-role
##
ansible-playbook top.yml --list-hosts
ansible-playbook top.yml

## Create a Kubernetes dev/demo cluster on VMs, using Ansible  

**This repo contains Ansible roles that let you quickly create a multi-node (master node plus worker nodes) Kubernetes cluster on virtual (or, with small modifications, on bare metal) machines. The current version has been tested on Ubuntu Linux.**

### Contents
[Kubernetes Cluster Description](#k8s-cluster-description)  
[Prerequisites](#prerequisites)  
[Getting Started](#getting-started)  
[Configuring Nodes](#configuring-nodes)  
[Node Hostnames and Admin Usernames](#node-hostnames-and-admin-usernames)  
[Modifying /etc/hosts](#modifying-etc-hosts)  
[Setting up Passwordless Access](#setting-up-passwordless-access)  
[Deploying Kubernetes](#deploying-k8s)     
[Deployment Phases](#deployment-phases)  
[Engage kubectl proxy](#engage-proxy)    
[Dashboard Access](#dashboard-access)  
[Authenticating to the Dashboard](#auth-to-dash)    
[Flight Checks](#flight-checks)  
[Resources](#resources)  
[Opsview Tutorials](#opsview-tutorials)

### <a name="k8s-cluster-description"></a>Kubernetes Cluster description
These Ansible roles and playbooks create a simple Kubernetes cluster on virtual machines preconfigured with Ubuntu 16.04 server as base OS. The deployment is automated using the Kubernetes Project's _kubeadm_ toolkit. The resulting cluster is identical to what is described in the article entitled _[Using kubeadm to Create a Cluster](https://kubernetes.io/docs/setup/independent/create-cluster-kubeadm/)_ in official Kubernetes documentation.

The cluster includes:

- One Kubernetes master node plus N worker nodes (default = 2 workers)
- Weave.net CNI networking
- kubectl CLI
- Kubernetes Dashboard

The playbooks also install:

- Helm (broken for now)

The deployment roles and playbooks can be customized to:

- Create clusters with more or fewer worker nodes (easy)
- Use alternative CNI networking fabrics (e.g., Calico, Flannel, etc.) (easy)
- _Not_ de-taint the master node (easy)
- Install additional Kubernetes components and tools (mileage varies)
- Use a different Ubuntu version or Linux distro as base OS (mileage varies)

### <a name="prerequisites"></a>Prerequisites
1. For Kubernetes nodes: Three or more virtual (or bare-metal) machines running [Ubuntu 16.04 LTS server](http://releases.ubuntu.com/16.04/ubuntu-16.04.4-server-amd64.iso.torrent?_ga=2.138459893.771820039.1526448425-1018235263.1526448425). Ubuntu 18.04 LTS will probably work as well, but this has not yet been tested.
1. For deployment and management: One VM or bare-metal machine running [Ansible 2.5+](http://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#installation-guide) on Ubuntu Desktop or other host OS. This machine should also be set up with standard utilities for terminal, ssh key management, text editing (e.g., [Atom](https://atom.io/)),  [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), and a standard browser such as Firefox or Chrome.   
1. 2 GB or more of RAM per machine (recommended: as much as possible)
1. 2 CPUs or more on the master (recommended: as many vCPUs as possible)
1. At least 20GB (preferably more) of hard disk or (preferably) SSD space
1. Full network connectivity between all machines (public or private network is fine). If using VirtualBox, a single vNIC per machine with 'bridged' or NAT' networking should enable machines to see one another and access internet.

### <a id="getting-started"></a>Getting Started  
Install Ansible, then begin by cloning this repo to your home directory on your management machine:

```  
cd /home/(your home directory name)
git clone https://github.com/genesiscloud/k8s-mvp.git
```

This will create a folder structure called **k8s-mvp/Deployment/Ansible/kube-cluster-role** from the top level of which you can execute the playbooks directly.

### <a id="configuring-nodes"></a>Configuring Nodes  
The Ansible roles and playbooks assume that you are configuring a
total of three VMs for use as Kubernetes nodes (one master and two
workers). Update the **hosts** file with the IP Addresses of the three
VM's (Note that 3 VM's suitable for this purpose can be created using
the script **/home/rich/k8s-mvp/VM/3-vms.sh**.

#### <a id="modifying-etc-hosts"></a>Modifying /etc/hosts
To facilitate terminal access to your nodes and simplify use of Ansible (but avoid the need to set up a DNS), we recommend adding your node hosts to your management machine's /etc/hosts file, per the following example. This can be done using:

```
sudo atom /etc/hosts
```   
Example:

```
127.0.0.1	localhost
127.0.1.1	management-machine-hostname

<IP of master node>   k8smaster
<IP of worker1 node>  k8sworker1
<IP of worker2 node>  k8sworker2

# ... etc.

```
Once changes are made, save the /etc/hosts file, then logout and back into your management machine (or restart it).

Test that you can ssh into your node machines with your password:

```
user@management-machine-hostname:~$ ssh stack@k8smaster
stack@k8smaster's password: <your password>
Welcome to Ubuntu 16.04.4 LTS (GNU/Linux 4.4.0-116-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

68 packages can be updated.
25 updates are security updates.


Last login: Wed May 16 02:29:26 2018
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

stack@k8smaster:~$
```
#### <a id="setting-up-passwordless-access"></a>Setting Up Passwordless Access  
To speed access to your nodes via ssh and to make life easier for Ansible, you should set up passwordless access to your Kubernetes node machines as follows:

###### Create an SSH Key
Create an ssh key, following the guidance in [this tutorial](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-on-ubuntu-1604) and save it in the default location (/your_home/.ssh). Do not protect your key with a password.

###### Copy your Key to the Nodes  
Using the same tutorial as guide, copy your key to each node, providing your password as requested:

Example:
```
ssh-copy-id stack@k8smaster  
```
Copy the key to each Kubernetes node machine in the same way.

###### Test Passwordless Login  
You should now test to see that you can log in to your machines as follows, without a password:

Example:

```
ssh stack@k8smaster  
```

### <a name="deploying-k8s"></a>Deploying Kubernetes  
You can now initiate Ansible deployment of your Kubernetes cluster from the toplevel of the folder **kube-cluster-role** as follows:

```
cd kube-cluster-role  
ansible-playbook -u stack -K top.yml   
```
... executing the toplevel playbook file, 'top.yml,' as user stack.

### <a name="deployment-phases"></a>Deployment Phases  

The top.yml playbook begins by installing Python 2 on all nodes (not, strictly speaking, an Ansible requirement -- Ansible can use Python 3, which is installed by default on Ubuntu -- but part of "standard" Ansible deployment patterns). Thereafter, deployment is carried out in several phases, by roles. To parse what's going on, it can be helpful to read the article _[Using kubeadm to Create a Cluster](https://kubernetes.io/docs/setup/independent/create-cluster-kubeadm/)_ carefully:

1. **The configure-nodes role is executed on all three nodes** (see **kube-cluster-role/configure-nodes/tasks/main.yml**)
   - The behavior of the vi editor is corrected for later convenience.  
   - Swap is turned off and the change made permanent.  
   - The server is restarted.
   - Opsview agent dependencies are installed.
   - The Opsview agent is installed.
   - Docker (a Kubernetes dependency) is installed.
   - The docker.service file is updated and the daemon restarted.
   - apt-transport-https is installed to enable installation of deb packages from remote web URLs.
   - Google GPG keys and repos are added and enabled.
   - The kubelet service is installed and started.
   - kubeadm (the deployer) and kubectl (the Kubernetes CLI) are installed.
   - The Kubernetes cgroup driver is matched to the one in use by Docker.
   - kubelet is restarted on each machine, and waits in a 'crashloop' (normal)  

1. **The create-k8s-master role is executed on the k8smaster node** (see **kube-cluster-role/create-k8s-master/tasks/main.yml**)  
 This involves executing **kubeadm init** on the master, creating the master node, then recovering kubeadm's output to preserve the returned **kubeadm join** command that will later be used to join workers to the master node. The returned output is saved as .txt in the **kube-cluster-role/current-cluster** directory. Note: the Weave CNI network that we install in step 3, below, does not require special parameterization of **kubeadm init** -- however, if you decide to change network fabrics, most of the other CNI network options do require parameters to be inserted here.  

1. **The install-weave role is executed on the k8smaster node** (see **kube-cluster-role/install-weave/tasks/main.yml**)  
 This involves making an iptables change required for Weave.Net, then setting up a new user (kubeuser) as a lower-permission user of kubectl -- doing this here so that associated .conf files can then be exported for use by the weave installer. Finally, the installer is applied, starting weave containers on the Kubernetes master node.

1. **The wrapup role is executed on the k8smaster node** (see **kube-cluster-role/wrapup/tasks/main.yml**)  
 This role de-taints the master node to permit general workloads to run there. It then installs the Kubernetes Dashboard, creates a user context for authenticating to it, runs **kubectl kube-system describe secrets** to dump cluster secrets and parses out a so-called 'bearer token' that will serve as a password for logging into the Dashboard, saving this on the management machine's local file system (in **kube-cluster-role/current-cluster**). Finally, it makes the non-administrative Kubernetes user able to call Docker without sudoing.

1. **The join-workers role is executed on the k8sworker1 and k8sworker2 nodes** (see **kube-cluster-role/join-workers/tasks/main.yml**)  
 Here, the **kubeadm join** command returned by **kubeadm init** is extracted from returned output and executed on each of the worker nodes, joining it to the cluster.

### <a name="engage-proxy"></a>Engage kubectl proxy
The **kubectl** CLI includes a proxy that can be used to facilitate connections to the Kubernetes master node by remote machines, providing a convenient way of enabling:

- Browser access to the Kubernetes Dashboard from a remote machine
- Access by Opsview Monitor for monitoring

To engage the proxy enabling both these things, log into the **k8smaster** node ...

```
ssh stack@k8smaster
```

... and execute **kubectl proxy** as follows:

```
kubectl proxy --port=8080 --address='0.0.0.0' --accept-hosts='^*$'
```

This permits access to the Kubernetes master's entrypoint on port 8080 from machines on the local network.

Killing the kubectl proxy is done by finding the PID of the running kubectl process on the master node:

```
ps -ef | grep kubectl
```
And then executing:

```
sudo kill -9 <kubectl_PID>
```

### <a name="dashboard-access"></a>Dashboard Access
Accessing the Kubernetes Dashboard from your management or other VM requires a several-step process:

1. Engage **kubectl proxy** (see above) on the Kubernetes master to expose the cluster entrypoint on a port (e.g., 8080).
1. Port-forward from your management computer to provide a tunnel for the browser:

```
ssh -L 9000:localhost:8080 stack@k8smaster
```
... where 9000 is an unused port. Thereafter, you can bring up the Dashboard on your management machine's browser by opening a tab to localhost:9000 on the following path:

```
http://localhost:9000/api/v1/namespaces/kube-system/services/https:kubernetes-dashboard:/proxy/#!/login
```

###### <a name="auth-to-dash"></a>Authenticating to the Kubernetes Dashboard  
To log into the Kubernetes Dashboard, the easiest method is to use bearer token authentication. The Ansible scripts retrieve a JSON payload containing (among other information) this bearer token for your administrative user, and save it in a local file: **kube-cluster-role/current_cluster/bearer-token.txt**

To retrieve the bearer token, it's helpful to use **jq** an open source Linux JSON parser. This can be installed on Ubuntu as follows:

```
sudo apt-get install jq  
```
Thereafter, you can switch to the current_cluster directory and extract the bearer token:

```
cd current_cluster
cat bearer-token.txt | jq ".stdout_lines[12]"  
```
The token, a long hex string, can then be copied into the appropriate field of the Dashboard's login dialog.

See the [Kubernetes Dashboard Guide](https://github.com/kubernetes/dashboard/wiki/Creating-sample-user) for more.

### <a name="flight-checks"></a>Flight Check
Some basic flight checks will confirm the health of your Kubernetes cluster. ssh to the master node with:

```
ssh stack@k8smaster  
```

And try some **kubectl** commands (Examples):

```
kubectl get pods --all-namespaces  (lists all running pods)
```
```
kubectl cluster-info  
```  

### <a name="resources"></a>Resources   

[Kubernetes basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/)  
[kubectl Overview](https://kubernetes.io/docs/reference/kubectl/overview/)  
[Kubernetes Dashboard Guide](https://github.com/kubernetes/dashboard/wiki/Creating-sample-user)  
