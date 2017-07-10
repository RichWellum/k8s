"ko.py" - Kubernetes OpenStack
==============================
    A tool to deploy kubernetes and OpenStack using Kolla Containers.

    This tool provides a method to deploy OpenStack on a Kubernetes
    Cluster using Kolla and Kolla-Kubernetes on bare metal servers or
    virtual machines. Virtual machines supported are Ubuntu and Centos.

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
    follow. Plus the verbose mode is helpful for seeing all the
    output.

    4. Contains a demo mode that walks the user through Kubernetes and
    OpenStack.

    5. This tool verifies it's completeness by generating a VM in the
    OpenStack Cluster.

    6. Leaves the user with a working OpenStack Cluster with all the
    basic services.

Mandatory Inputs
================
    1. mgmt_int (network_interface):
    Name of the interface to be used for management operations.

    The `network_interface` variable is the interface to which Kolla binds API
    services. For example, when starting Mariadb, it will bind to the IP on the
    interface list in the ``network_interface`` variable.

    2. mgmt_ip:
    IP Address of management interface (mgmt_int)

    3. neutron_int (neutron_external_interface):
    Name of the interface to be used for Neutron operations.

    The `neutron_external_interface` variable is the interface that will be used
    for the external bridge in Neutron. Without this bridge the deployment instance
    traffic will be unable to access the rest of the Internet.

    4. keepalived:
    An unused IP address in the network to act as a VIP for
    `kolla_internal_vip_address`.

    The VIP will be used with keepalived and added to the `api_interface` as
    specified in the ``globals.yml``
