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

    [rwellum@centosk8s k8s]$ ./ko.py eth0 eth1 -mi 3.3.3.3 -vi 5.5.5.5 -h
    usage: ko.py [-h] [-mi MGMT_IP] [-vi VIP_IP] [-lv] [-it IMAGE_TAG]
                 [-hv HELM_VERSION] [-kv K8S_VERSION] [-cv CNI_VERSION]
                 [-av ANSIBLE_VERSION] [-jv JINJA2_VERSION] [-c] [-cc] [-k8s]
                 [-os] [-n] [-ec] [-v] [-d] [-f]
                 MGMT_INT NEUTRON_INT

    This tool provides a method to deploy OpenStack on a Kubernetes Cluster using Kolla and Kolla-Kubernetes on bare metal servers or virtual machines. Virtual machines supported are Ubuntu and Centos.
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
      -lv, --latest_version
                            Try to install all the latest versions of tools,
                            overidden by individual tool versions if requested.
      -it IMAGE_TAG, --image_tag IMAGE_TAG
                            Specify a different Kolla image tage to the
                            default(4.0.0)
      -hv HELM_VERSION, --helm_version HELM_VERSION
                            Specify a different helm version to the default(2.5.0)
      -kv K8S_VERSION, --k8s_version K8S_VERSION
                            Specify a different kubernetes version to the
                            default(1.7.0)
      -cv CNI_VERSION, --cni_version CNI_VERSION
                            Specify a different kubernetes-cni version to the
                            default(0.5.1-00)
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
      -os, --openstack      Build OpenStack on an existing Kubernetes Cluster
      -n, --nslookup        Pause for the user to manually test nslookup in
                            kubernetes cluster
      -ec, --edit_config    Pause to allow the user to edit the global.yaml and
                            the cloud.yaml files - for custom configuration
      -v, --verbose         Turn on verbose messages
      -d, --demo            Display some demo information and offer to move on
      -f, --force           When used in conjunction with --demo - it will proceed
                            without user input

    E.g.: k8s.py eth0 10.240.43.250 eth1 10.240.43.251 -v -kv 1.6.2 -hv 2.4.2
    [rwellum@centosk8s k8s]$

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

    [rwellum@centosko openstack]$ ../k8s/ko.py eth0 eth1

    *******************************************
    Kubernetes - Bring up a Kubernetes Cluster:
    *******************************************

    Linux info:      ('CentOS Linux', '7.3.1611', 'Core')

    ../k8s/ko.py - Networking:
    Management Int:  eth0
    Management IP:   10.240.43.77
    Neutron Int:     eth1
    VIP Keepalive:   10.240.43.113

    ../k8s/ko.py - Versions:
    Docker version:  1.12.6
    Kolla Image Tag: 4.0.0
    Helm version:    2.5.0
    K8s version:     1.7.0
    Ansible version: 2.2.0.0
    Jinja2 version:  2.8.1


    (01/15) Kubernetes - Update and install base tools
    (02/15) Kubernetes - Setup NTP
    (03/15) Kubernetes - Turn off SELinux
    (03/15) Kubernetes - Turn off firewall
    (04/15) Kubernetes - Creating kubernetes repo, installing Kubernetes packages
    (05/15) Kubernetes - Start docker and setup the DNS server with the service CIDR
    (06/15) Kubernetes - Reload the hand-modified service files
    (07/15) Kubernetes - Enable and start kubelet
    (08/15) Kubernetes - Fix iptables to enable bridging
    (09/15) Kubernetes - Deploying Kubernetes with kubeadm
    (10/15) Kubernetes - Load kubeadm credentials into the syste
    (08/15) Kubernetes - Fix iptables to enable bridging
    (09/15) Kubernetes - Deploying Kubernetes with kubeadm
    (10/15) Kubernetes - Load kubeadm credentials into the system
      Note "kubectl get pods --all-namespaces" should work now
    (11/15) Kubernetes - Wait for basic Kubernetes (6 pods) infrastructure:
      *Pod status after 10 seconds, pods up 0:6 - sleep 10 seconds and retry*m
      Note "kubectl get pods --all-namespaces" should work now
    (11/15) Kubernetes - Wait for basic Kubernetes (6 pods) infrastructure:
      *Pod status after 10 seconds, pods up 0:6 - sleep 10 seconds and retry*
      *Pod status after 20 seconds, pods up 2:6 - sleep 10 seconds and retry*
      *Pod status after 30 seconds, pods up 2:6 - sleep 10 seconds and retry*
      *Pod status after 40 seconds, pods up 2:6 - sleep 10 seconds and retry*
      *Pod status after 50 seconds, pods up 2:6 - sleep 10 seconds and retry*
      *Pod status after 60 seconds, pods up 5:6 - sleep 10 seconds and retry*
      *All pods 6/6 are started, continuing*
    (12/15) Kubernetes - Add API Server
    (13/15) Kubernetes - Create RBAC and Deploy the Canal CNI driver
      Wait for all pods to be in Running state:
        *2 pod(s) are not in Running state*
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (14/15) Kubernetes - Mark master node as schedulable
    (15/15) Kubernetes - Test 'nslookup kubernetes' - bring up test container
      Wait for all pods to be in Running state:
        *1 pod(s) are not in Running state*
        *All pods are in Running state*


    ************************************
    Kubernetes Cluster is up and running
    ************************************



    **************************
    Kolla - install OpenStack:
    **************************

    (01/42) Kolla - Overide default RBAC settings
    (02/42) Kolla - Install and deploy Helm version 2.5.0 - Tiller pod
      Wait for all pods to be in Running state:
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (02/42) Kolla - Helm successfully installed
    (03/42) Kolla - Clone kolla-ansible
    (04/42) Kolla - Clone kolla-kubernetes
    (05/42) Kolla - Install kolla-ansible and kolla-kubernetes
    (06/42) Kolla - Copy default kolla-ansible configuration to /etc
    (07/42) Kolla - Copy default kolla-kubernetes configuration to /etc
    (08/42) Kolla - Setup Loopback LVM for Cinder
    (09/42) Kolla - Install Python Openstack Client
    (10/42) Kolla - Generate default passwords via SPRNG
    (11/42) Kolla - Create a Kubernetes namespace to isolate this Kolla deployment
    (12/42) Kolla - Label Nodes:
      Label the AIO node as 'kolla_compute'
      Label the AIO node as 'kolla_controller'
    (13/42) Kolla - Modify global.yml to setup network_interface and neutron_interface
    (14/42) Kolla - Add default config to globals.yml
    (15/42) Kolla - Enable qemu
    (16/42) Kolla - Generate the default configuration
    (17/42) Kolla - Generate the Kubernetes secrets and register them with Kubernetes
    (18/42) Kolla - Create and register the Kolla config maps
    (19/42) Kolla - Enable resolv.conf workaround
    (20/42) Kolla - Build all Helm microcharts, service charts, and metacharts
    (21/42) Kolla - Verify helm images
    Kolla - 193 Helm images created
    (22/42) Kolla - Create a cloud.yaml
    (23/42) Kolla - Helm Install service chart: openvswitch
      Wait for all pods to be in Running state:
        *2 pod(s) are not in Running state*
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (24/42) Kolla - Helm Install service chart: keepalived-daemonset
      Wait for all pods to be in Running state:
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (24/42) Kolla - Helm Install service chart: mariadb
      Wait for all pods to be in Running state:
        *2 pod(s) are not in Running state*
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (25/42) Kolla - Helm Install service chart: rabbitmq
    (26/42) Kolla - Helm Install service chart: memcached
    (27/42) Kolla - Helm Install service chart: keystone
    (28/42) Kolla - Helm Install service chart: glance
    (29/42) Kolla - Helm Install service chart: cinder-control
    (30/42) Kolla - Helm Install service chart: cinder-volume-lvm
    (31/42) Kolla - Helm Install service chart: horizon
    (32/42) Kolla - Helm Install service chart: neutron
      Wait for all pods to be in Running state:
        *46 pod(s) are not in Running state*
        *45 pod(s) are not in Running state*
        *44 pod(s) are not in Running state*
        *43 pod(s) are not in Running state*
        *42 pod(s) are not in Running state*
        *41 pod(s) are not in Running state*
        *40 pod(s) are not in Running state*
        *39 pod(s) are not in Running state*
        *38 pod(s) are not in Running state*
        *37 pod(s) are not in Running state*
        *36 pod(s) are not in Running state*
        *35 pod(s) are not in Running state*
        *32 pod(s) are not in Running state*
        *31 pod(s) are not in Running state*
        *30 pod(s) are not in Running state*
        *29 pod(s) are not in Running state*
        *28 pod(s) are not in Running state*
        *24 pod(s) are not in Running state*
        *22 pod(s) are not in Running state*
        *23 pod(s) are not in Running state*
        *16 pod(s) are not in Running state*
        *15 pod(s) are not in Running state*
        *12 pod(s) are not in Running state*
        *10 pod(s) are not in Running state*
        *9 pod(s) are not in Running state*
        *8 pod(s) are not in Running state*
        *6 pod(s) are not in Running state*
        *5 pod(s) are not in Running state*
        *4 pod(s) are not in Running state*
        *3 pod(s) are not in Running state*
        *2 pod(s) are not in Running state*
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (33/42) Kolla - Helm Install service chart: nova-control
    (34/42) Kolla - Helm Install service chart: nova-compute
      Wait for all pods to be in Running state:
        *23 pod(s) are not in Running state*
        *22 pod(s) are not in Running state*
        *21 pod(s) are not in Running state*
        *19 pod(s) are not in Running state*
        *17 pod(s) are not in Running state*
        *16 pod(s) are not in Running state*
        *15 pod(s) are not in Running state*
        *12 pod(s) are not in Running state*
        *10 pod(s) are not in Running state*
        *9 pod(s) are not in Running state*
        *8 pod(s) are not in Running state*
        *7 pod(s) are not in Running state*
        *3 pod(s) are not in Running state*
        *2 pod(s) are not in Running state*
        *1 pod(s) are not in Running state*
        *All pods are in Running state*
    (35/42) Kolla - Final Kolla Kubernetes OpenStack pods for namespace kube-system:
    NAME                               READY     STATUS    RESTARTS   AGE
    canal-3fzw2                        3/3       Running   0          35m
    etcd-centosko                      1/1       Running   1          35m
    kube-apiserver-centosko            1/1       Running   0          35m
    kube-controller-manager-centosko   1/1       Running   1          35m
    kube-dns-2425271678-k5jpw          3/3       Running   0          36m
    kube-proxy-m8222                   1/1       Running   0          36m
    kube-scheduler-centosko            1/1       Running   1          35m
    tiller-deploy-3235729489-nwx6v     1/1       Running   0          33m

    (36/42) Kolla - Final Kolla Kubernetes OpenStack pods for namespace kolla:
    NAME                                      READY     STATUS    RESTARTS   AGE
    cinder-api-2775249182-2wprn               3/3       Running   0          21m
    cinder-scheduler-0                        1/1       Running   0          21m
    cinder-volume-vjbvq                       1/1       Running   3          21m
    glance-api-1563514938-p1tpb               1/1       Running   0          21m
    glance-registry-480622726-h1vfl           3/3       Running   0          21m
    horizon-4102269680-ps443                  1/1       Running   0          20m
    iscsid-fcn83                              1/1       Running   0          21m
    keepalived-5wn6f                          1/1       Running   0          23m
    keystone-4247253593-56ks2                 1/1       Running   0          21m
    mariadb-0                                 1/1       Running   0          23m
    memcached-3612446176-kjbhd                2/2       Running   0          21m
    neutron-dhcp-agent-l2sx6                  1/1       Running   0          20m
    neutron-l3-agent-network-t6ngw            1/1       Running   0          20m
    neutron-metadata-agent-network-79cr1      1/1       Running   0          20m
    neutron-openvswitch-agent-network-wcdxj   1/1       Running   0          20m
    neutron-server-4156805867-7zk39           3/3       Running   0          20m
    nova-api-4162245109-qbgc6                 3/3       Running   0          9m
    nova-api-create-cell-c1h92                1/1       Running   0          9m
    nova-compute-2mqps                        1/1       Running   0          9m
    nova-conductor-0                          1/1       Running   0          9m
    nova-consoleauth-0                        1/1       Running   0          9m
    nova-libvirt-k5096                        1/1       Running   0          9m
    nova-novncproxy-1208748992-fz5gk          3/3       Running   0          9m
    nova-scheduler-0                          1/1       Running   0          9m
    openvswitch-ovsdb-network-gqk04           1/1       Running   0          25m
    openvswitch-vswitchd-network-bvkkz        1/1       Running   0          25m
    placement-api-1550969126-1zr6l            1/1       Running   0          9m
    rabbitmq-0                                1/1       Running   0          21m
    tgtd-hj99f                                1/1       Running   0          21m

    (37/42) Kolla - Create a keystone admin account and source in to it
    (38/42) Kolla - Create a demo vm in our OpenStack cluster
      Kubernetes - Wait for VM demo1 to be in running state:
        Kubernetes - VM demo1 is not Running yet
        Kubernetes - VM demo1 is not Running yet
        Kubernetes - VM demo1 is not Running yet
        Kubernetes - VM demo1 is not Running yet
        Kubernetes - VM demo1 is Running
    (39/42) Kolla - Create floating ip
    (40/42) Kolla - Allow Ingress by changing neutron rules
    (41/42) Kolla - nova list
    +--------------------------------------+-------+--------+------------+-------------+-------------------------------+
    | ID                                   | Name  | Status | Task State | Power State | Networks                      |
    +--------------------------------------+-------+--------+------------+-------------+-------------------------------+
    | f67dc3b5-08f9-4b55-8cb1-3b0ba5ba54d9 | demo1 | ACTIVE | -          | Running     | demo-net=10.0.0.6, 10.0.2.154 |
    +--------------------------------------+-------+--------+------------+-------------+-------------------------------+

    (42/42) Kolla - To Access Horizon:
      Point your browser to: 10.240.43.77

      OS_PASSWORD=icCX8aqjYVVp7pgNT3x1RoNjTUtlqZEgynAMBJLe

      OS_USERNAME=admin

    [rwellum@centosko openstack]$
