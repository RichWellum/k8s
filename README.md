"ko.py" - Kubernetes OpenStack
==============================
    A tool to deploy kubernetes and OpenStack using Kolla Containers.

    This tool provides a method to deploy OpenStack on a Kubernetes
    Cluster using Kolla and Kolla-Kubernetes on bare metal servers or
    virtual machines. Virtual machines supported are Ubuntu and
    Centos.

    This tool is designed to be a fun way to play with this technology. In
    no way is it supposed to be production ready. It contains both a
    verbose mode to see what is going on during deployment and a demo
    mode which attempts to walk the user through all the steps.

    It contains a lot of options to play with different tool versions
    so it can be useful to verify and debug when the environment has
    changed - say a kubernetes upgrade.

    It currently works only with the kolla-kubernetes methodology but
    I intend to expand it to use openstack-helm so the user can
    compare and contrast.

    All comments, suggestions and improvements welcome.

    richwellum@gmail.com

Help
====

    ubuntu@ubuntuk8s:~/os$ ../k8s/ko.py ens3 ens4 -cn -iv pike -dr rwellum -cni weave --logs -h
    usage: ko.py [-h] [-mi MGMT_IP] [-vi VIP_IP] [-iv IMAGE_VERSION]
                 [-hv HELM_VERSION] [-kv K8S_VERSION] [-av ANSIBLE_VERSION]
                 [-jv JINJA2_VERSION] [-c] [-cc] [-k8s] [-cm] [-os] [-n] [-eg]
                 [-ec] [-v] [-d] [-f] [-cn] [-dm] [-ng] [-bd BASE_DISTRO]
                 [-dr DOCKER_REPO] [-cni CNI] [-l] [-drr]
                 MGMT_INT NEUTRON_INT

    This tool provides a method to deploy OpenStack on a Kubernetes Cluster using Kolla
    and Kolla-Kubernetes on bare metal servers or virtual machines.
    Virtual machines supported are Ubuntu and Centos.
    Usage as simple as: "ko.py eth0 eth1"
    The host machine must satisfy the following minimum requirements:
    - 2 network interfaces
    - 8GB min, 16GB preferred - main memory
    - 40G min, 80GB preferred - disk space
    - 2 CPUs Min, 4 preferred - CPUs
    Root access to the deployment host machine is required.

    positional arguments:
      MGMT_INT              The interface to which Kolla binds API services, E.g:
                            eth0
      NEUTRON_INT           The interface that will be used for the external
                            bridge in Neutron, E.g: eth1

    optional arguments:
      -h, --help            show this help message and exit
      -mi MGMT_IP, --mgmt_ip MGMT_IP
                            Provide own MGMT ip address Address, E.g:
                            10.240.83.111
      -vi VIP_IP, --vip_ip VIP_IP
                            Provide own Keepalived VIP, used with keepalived,
                            should be an unused IP on management NIC subnet, E.g:
                            10.240.83.112
      -iv IMAGE_VERSION, --image_version IMAGE_VERSION
                            Specify a different Kolla image version to the default
                            (ocata)
      -hv HELM_VERSION, --helm_version HELM_VERSION
                            Specify a different helm version to the default(2.7.2)
      -kv K8S_VERSION, --k8s_version K8S_VERSION
                            Specify a different kubernetes version to the
                            default(1.8.4) - note 1.8.0 is the minimum supported
      -av ANSIBLE_VERSION, --ansible_version ANSIBLE_VERSION
                            Specify a different ansible version to the
                            default(2.2.0.0)
      -jv JINJA2_VERSION, --jinja2_version JINJA2_VERSION
                            Specify a different jinja2 version to the
                            default(2.8.1)
      -c, --cleanup         YMMV: Cleanup existing Kubernetes cluster before
                            creating a new one. Because LVM is not cleaned up,
                            space will be used up. "-cc" is far more reliable but
                            requires a reboot
      -cc, --complete_cleanup
                            Cleanup existing Kubernetes cluster then exit,
                            rebooting host is advised
      -k8s, --kubernetes    Stop after bringing up kubernetes, do not install
                            OpenStack
      -cm, --create_minion  Do not install Kubernetes or OpenStack, useful for
                            preparing a multi-node minion
      -os, --openstack      Build OpenStack on an existing Kubernetes Cluster
      -n, --nslookup        Pause for the user to manually test nslookup in
                            kubernetes cluster
      -eg, --edit_globals   Pause to allow the user to edit the globals.yaml file
                            - for custom configuration
      -ec, --edit_cloud     Pause to allow the user to edit the cloud.yaml file -
                            for custom configuration
      -v, --verbose         Turn on verbose messages
      -d, --demo            Display some demo information and offer to move on
      -f, --force           When used in conjunction with --demo - it will proceed
                            without user input
      -cn, --create_network
                            Try to create a OpenStack network model, configure
                            neutron, download and install a test VM
      -dm, --dev_mode       Adds option to modify kolla and more info
      -ng, --no_git         Select this to not override git repos previously
                            downloaded
      -bd BASE_DISTRO, --base_distro BASE_DISTRO
                            Specify a base container image to the default(centos),
                            like "ubuntu"
      -dr DOCKER_REPO, --docker_repo DOCKER_REPO
                            Specify a different docker repo the default(lokolla),
                            for exampe "rwellum" has the latest pike images
      -cni CNI, --cni CNI   Specify a different CNI/SDN tothe default(canal), like
                            "weave"
      -l, --logs            Experimental, installs a patch set and runs fluentd
                            container to gather logs.
      -drr, --dry_run       Dry run commands only.

    E.g.: k8s.py eth0 eth1 -kv 1.6.2 -hv 2.4.2 -iv pike
    ubuntu@ubuntuk8s:~/os$


Host machine requirements
=========================
    The host machine must satisfy the following minimum requirements:

    - 2 network interfaces
    - 8GB min, 16GB preferred - main memory
    - 40G min, 80GB preferred disk space
    - 2 CPU's Min, 4 preferred CPU's

    Root access to the deployment host machine is required.

Prerequisites
=============
    Verify the state of network interfaces. If using a VM spawned on
    OpenStack as the host machine, the state of the second interface will be DOWN
    on booting the VM.

       ip addr show

    Bring up the second network interface if it is down.

       ip link set ens4 up

    Verify if the second interface has an IP address.

       ip addr show

Preceding
=========
    This relies heavily on the OpenStack kolla-kubernetes project and in
    particular the Bare Metal Deployment Guide:

    https://docs.openstack.org/developer/kolla-kubernetes/deployment-guide.html

    However support will be added to also install OpenStack with the
    openstack-helm project.

Purpose
=======

    The purpose of this tool, when there are so many others out there is:

    1. Many tools don't support both Centos and Ubuntu with no input
    from the user.

    2. I like to play with versions of all the supporting tools, it
    helps when users report issues when they upgrade say helm, or
    docker, or kubernetes.

    3. I like the output of my tool - it's succinct and easy to
    follow. Plus the verbose mode is helpful for seeing all the output.

    4. Contains a demo mode that walks the user through Kubernetes and OpenStack.

    5. This tool verifies it's completeness by generating a VM in the
    OpenStack Cluster.

    6. Leaves the user with a working OpenStack Cluster with all the
    basic services.

    7. Very simple to run - just requires two NIC's

    8. Lots of options to customize - even edit globals.yaml and cloud.yaml

Mandatory Inputs
================

    1. mgmt_int (network_interface):
    Name of the interface to be used for management operations.

    The `network_interface` variable is the interface to which Kolla binds API
    services. For example, when starting Mariadb, it will bind to the IP on the
    interface list in the ``network_interface`` variable.

    2. neutron_int (neutron_external_interface):
    Name of the interface to be used for Neutron operations.

    The `neutron_external_interface` variable is the interface that will be used
    for the external bridge in Neutron. Without this bridge the deployment instance
    traffic will be unable to access the rest of the Internet.

Example Output
==============

    ubuntu@ubuntuk8s:~/os$ ../k8s/ko.py ens3 ens4 -cn -iv pike -dr rwellum -cni weave --logs


*******************************************
Kubernetes - Bring up a Kubernetes Cluster:
*******************************************

    Linux Host Info:    ('Ubuntu', '16.04', 'xenial')

    Networking Info:
      Management Int:     ens3
      Neutron Int:        ens4
      Management IP:      10.100.100.14
      VIP Keepalive:      10.100.100.135
      CNI/SDN:            weave

    Tool Versions:
      Docker version:     1.13.1
      Helm version:       2.7.2
      K8s version:        1.8.4
      Ansible version:    2.2.0.0
      Jinja2 version:     2.8.1

    OpenStack Versions:
      Openstack version:  pike (5.0.1)
      Base image version: centos
      Docker repo:        rwellum

    Other Info:
      Logging enabled:    True
      Dev mode enabled:   False
      Create Network:     True
      Demo mode:          False
      Edit Cloud:         False
      Edit Globals:       False


    (01/15) Kubernetes - Installing base tools
    (02/15) Kubernetes - Setup NTP
    (03/15) Kubernetes - Turn off firewall and ISCSID
    (04/15) Kubernetes - Creating Kubernetes repo, installing Kubernetes packages
    (05/15) Kubernetes - Start docker and setup the DNS server with the service CIDR
    (06/15) Kubernetes - Reload the hand-modified service files
    (07/15) Kubernetes - Enable and start kubelet
    (08/15) Kubernetes - Fix iptables to enable bridging
    (09/15) Kubernetes - Deploying Kubernetes with kubeadm (Slow!)
      You can now join any number of machines by running the following on each node as root:
      kubeadm join --token 6a3654.dd285959559ce23b 10.100.100.14:6443 --discovery-token-ca-cert-hash sha256:6f73da0c963f6ae6adee483863ed7ceaf3b23730b0d2bfa5cac77b40746fa9b3
    (10/15) Kubernetes - Load kubeadm credentials into the system
      Note "kubectl get pods --all-namespaces" should work now
    (11/15) Kubernetes - Wait for basic Kubernetes (6 pods) infrastructure
      *Running pod(s) status after 20 seconds 2:6*
      *Running pod(s) status after 60 seconds 5:6*
      *All pods 6/6 are started, continuing*
    (12/15) Kubernetes - Add API Server
    (13/15) Kubernetes - Deploy pod network SDN using Weave CNI
      Wait for all pods to be in Running state:
        *02 pod(s) are not in Running state*
        *01 pod(s) are not in Running state*
        *All pods are in Running state*
    (14/15) Kubernetes - Mark master node as schedulable by untainting the node
    (15/15) Kubernetes - Test 'nslookup kubernetes' - bring up test pod
      Wait for all pods to be in Running state:
        *01 pod(s) are not in Running state*
        *All pods are in Running state*


    ************************************
    Kubernetes Cluster is up and running
    ************************************



    **************************
    Kolla - install OpenStack:
    **************************

    (01/45) Kolla - Overide default RBAC settings
    (02/45) Kolla - Install and deploy Helm version 2.7.2 - Tiller pod
      Wait for all pods to be in Running state:
        *01 pod(s) are not in Running state*
        *All pods are in Running state*
    (03/45) Kolla - Helm successfully installed
    (04/45) Kolla - Clone kolla-ansible
    (05/45) Kolla - Clone kolla-kubernetes
    (06/45) Kolla - Install kolla-ansible and kolla-kubernetes
    (07/45) Kolla - Copy default kolla-ansible configuration to /etc
    (08/45) Kolla - Copy default kolla-kubernetes configuration to /etc
    (09/45) Kolla - Setup Loopback LVM for Cinder (Slow!)
    (10/45) Kolla - Install Python Openstack Client
    (11/45) Kolla - Generate default passwords via SPRNG
    (12/45) Kolla - Create a Kubernetes namespace "kolla" to isolate this Kolla deployment
    (13/45) Kolla - Label Nodes:
      Label the AIO node as 'kolla_compute'
      Label the AIO node as 'kolla_controller'
    (14/45) Kolla - Modify global.yml to setup network_interface and neutron_interface
    (15/45) Kolla - Add default config to globals.yml
    (16/45) Kolla - Generate the default configuration
    (17/45) Kolla - Set libvirt type to QEMU
    (18/45) Kolla - Generate the Kubernetes secrets and register them with Kubernetes
    (19/45) Kolla - Create and register the Kolla config maps
    (20/45) Kolla - Build all Helm microcharts, service charts, and metacharts (Slow!)
    (21/45) Kolla - Verify number of helm images
      195 Helm images created
    (22/45) Kolla - Create a version 5+ cloud.yaml
    (23/45) Kolla - Helm Install service chart: \--'openvswitch'--/
      Wait for all pods to be in Running state:
        *02 pod(s) are not in Running state*
        *01 pod(s) are not in Running state*
        *All pods are in Running state*
    (24/45) Kolla - Helm Install service chart: \--'mariadb'--/
      Wait for all pods to be in Running state:
        *02 pod(s) are not in Running state*
        *01 pod(s) are not in Running state*
        *All pods are in Running state*
    (25/45) Kolla - Helm Install service chart: \--'rabbitmq'--/
    (26/45) Kolla - Helm Install service chart: \--'memcached'--/
    (27/45) Kolla - Helm Install service chart: \--'keystone'--/
    (28/45) Kolla - Helm Install service chart: \--'glance'--/
    (29/45) Kolla - Helm Install service chart: \--'cinder-control'--/
    (30/45) Kolla - Helm Install service chart: \--'cinder-volume-lvm'--/
    (31/45) Kolla - Helm Install service chart: \--'horizon'--/
    (32/45) Kolla - Helm Install service chart: \--'neutron'--/
      Wait for all pods to be in Running state:
        *45 pod(s) are not in Running state*
        *44 pod(s) are not in Running state*
        *43 pod(s) are not in Running state*
        *42 pod(s) are not in Running state*
        *41 pod(s) are not in Running state*
        *40 pod(s) are not in Running state*
        *39 pod(s) are not in Running state*
        *35 pod(s) are not in Running state*
        *33 pod(s) are not in Running state*
        *32 pod(s) are not in Running state*
        *29 pod(s) are not in Running state*
        *28 pod(s) are not in Running state*
        *27 pod(s) are not in Running state*
        *26 pod(s) are not in Running state*
        *23 pod(s) are not in Running state*
        *20 pod(s) are not in Running state*
        *18 pod(s) are not in Running state*
        *17 pod(s) are not in Running state*
        *15 pod(s) are not in Running state*
        *14 pod(s) are not in Running state*
        *11 pod(s) are not in Running state*
        *10 pod(s) are not in Running state*
        *08 pod(s) are not in Running state*
        *07 pod(s) are not in Running state*
        *06 pod(s) are not in Running state*
        *04 pod(s) are not in Running state*
        *03 pod(s) are not in Running state*
        *01 pod(s) are not in Running state*
        *All pods are in Running state*
    (33/45) Kolla - Helm Install service chart: \--'nova-control'--/
    (34/45) Kolla - Helm Install service chart: \--'nova-compute'--/
      Wait for all pods to be in Running state:
        *23 pod(s) are not in Running state*
        *22 pod(s) are not in Running state*
        *20 pod(s) are not in Running state*
        *19 pod(s) are not in Running state*
        *17 pod(s) are not in Running state*
        *16 pod(s) are not in Running state*
        *15 pod(s) are not in Running state*
        *14 pod(s) are not in Running state*
        *13 pod(s) are not in Running state*
        *12 pod(s) are not in Running state*
        *11 pod(s) are not in Running state*
        *10 pod(s) are not in Running state*
        *09 pod(s) are not in Running state*
        *08 pod(s) are not in Running state*
        *04 pod(s) are not in Running state*
        *All pods are in Running state*
    (35/45) Kolla - Install Fluentd container
    (36/45) Kolla - Final Kolla Kubernetes OpenStack pods for namespace kube-system:
    NAME                                READY     STATUS    RESTARTS   AGE
    etcd-ubuntuk8s                      1/1       Running   0          18m
    kube-apiserver-ubuntuk8s            1/1       Running   0          18m
    kube-controller-manager-ubuntuk8s   1/1       Running   1          18m
    kube-dns-545bc4bfd4-hqr7f           3/3       Running   0          19m
    kube-proxy-cwxqj                    1/1       Running   0          19m
    kube-scheduler-ubuntuk8s            1/1       Running   1          18m
    tiller-deploy-5b9d65c7f-kl6hz       1/1       Running   0          16m
    weave-net-rjnch                     2/2       Running   0          17m
    (37/45) Kolla - Final Kolla Kubernetes OpenStack pods for namespace kolla:
    NAME                                      READY     STATUS    RESTARTS   AGE
    cinder-api-75cf6b6c7b-fblq4               3/3       Running   0          6m
    cinder-scheduler-0                        1/1       Running   0          6m
    cinder-volume-b42fj                       1/1       Running   3          6m
    glance-api-74896f7757-vgmlx               1/1       Running   0          6m
    glance-registry-57886f64c8-zp9dn          3/3       Running   0          6m
    horizon-cb5f44bc7-7mg88                   1/1       Running   0          6m
    iscsid-28qz5                              1/1       Running   0          6m
    keystone-b94f4dd4-zndqp                   1/1       Running   0          6m
    mariadb-0                                 1/1       Running   0          7m
    memcached-f855d988d-8c89n                 2/2       Running   0          6m
    neutron-dhcp-agent-mj7pp                  1/1       Running   0          6m
    neutron-l3-agent-network-p9swg            1/1       Running   0          6m
    neutron-metadata-agent-network-8krdq      1/1       Running   0          6m
    neutron-openvswitch-agent-network-8mhgm   1/1       Running   0          6m
    neutron-server-79f59644c5-2bc7l           3/3       Running   0          6m
    nova-api-64c54b66df-8cjxq                 3/3       Running   0          2m
    nova-api-create-cell-r7kzw                1/1       Running   0          2m
    nova-compute-zl5f9                        1/1       Running   0          2m
    nova-conductor-0                          1/1       Running   0          2m
    nova-consoleauth-0                        1/1       Running   0          2m
    nova-libvirt-k5z95                        1/1       Running   0          2m
    nova-novncproxy-6ff8fbb6f8-p9zx8          2/3       Running   0          2m
    nova-scheduler-0                          1/1       Running   0          2m
    openvswitch-ovsdb-network-8xv9n           1/1       Running   0          7m
    openvswitch-vswitchd-network-rn2mt        1/1       Running   0          7m
    placement-api-d998c47c4-4qcbd             1/1       Running   0          2m
    rabbitmq-0                                1/1       Running   0          6m
    tgtd-vzbf7                                1/1       Running   0          6m
    (38/45) Kolla - Create a keystone admin account and source in to it
    (39/45) Kolla - Allow Ingress by changing neutron rules
    (40/45) Kolla - Fix Nova, various issues, nova scheduler pod will be restarted
      Wait for all pods to be in Running state:
        *01 pod(s) are not in Running state*
        *All pods are in Running state*
    (41/45) Kolla - Configure Neutron, pull images
    (42/45) Kolla - Create a demo VM in our OpenStack cluster
    To create a demo image VM do:
    .  ~/keystonerc_admin; openstack server create --image cirros --flavor m1.tiny --key-name mykey --nic net-id=f62cdbad-b8f3-4f6d-8b0e-8f911b6b58a8 test
      Kubernetes - Wait for VM demo1 to be in running state:
        *Kubernetes - VM demo1 is not Running yet - wait 15s*
        *Kubernetes - VM demo1 is not Running yet - wait 15s*
        *Kubernetes - VM demo1 is not Running yet - wait 15s*
        *Kubernetes - VM demo1 is Running*
    (43/45) Kolla - Create floating ip
    (44/45) Kolla - nova list to see floating IP and demo VM
    +--------------------------------------+-------+--------+------------+-------------+------------------------+
    | ID                                   | Name  | Status | Task State | Power State | Networks               |
    +--------------------------------------+-------+--------+------------+-------------+------------------------+
    | 64383b56-7785-4d71-83f3-056e0117cf8d | demo1 | ACTIVE | -          | Running     | public1=192.168.10.166 |
    +--------------------------------------+-------+--------+------------+-------------+------------------------+
    (45/45) Kolla - To Access Horizon:
      Point your browser to: 10.3.3.237
      OS_PASSWORD=szkZ2hbOdeX6LgJXqnYXMNfsExVLGXDnyup67MMb
      OS_USERNAME=admin


    **************************************************************************
    Successfully deployed Kolla-Kubernetes. OpenStack Cluster is ready for use
    **************************************************************************
