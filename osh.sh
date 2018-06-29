#!/bin/bash

# To be converted to python
sudo -v

# Clean up previous installation
rm -rf openstack-helm*

# Clone newly
git clone https://git.openstack.org/openstack/openstack-helm-infra.git
git clone https://git.openstack.org/openstack/openstack-helm.git

# Resolv.conf has to reflect the network that k8s is on
# For example:
# #nameserver 192.168.122.1
# search openstack.svc.cluster.local svc.cluster.local cluster.local
# nameserver 10.3.3.10
# options ndots:5 timeout:1 attempts:1
# Use: kubectl -n kube-system get svc kube-dns -o json | jq -r .spec.clusterIP
# to determine ip to add
# But really this should be followed:
# https://github.com/openstack/openstack-helm-infra/blob/master/tools/images/kubeadm-aio/assets/opt/playbooks/roles/deploy-kubelet/templates/resolv.conf.j2#L2

# Note that if this is not a clean deployment then ceph needs to be cleaned up
# first
# Install ceph client
sudo apt install ceph-common -y

# Build all helm charts
helm repo add local http://localhost:8879/charts
pushd openstack-helm-infra
make clean
git pull
make all
popd

pushd openstack-helm
make clean
git pull
make all

# Start helm server if not already
helm serve &
helm repo add local http://localhost:8879/charts

# Label nodes
kubectl label nodes osh openstack-helm-node-class=primary
kubectl label nodes osh openstack-control-plane=enabled
kubectl label nodes osh openstack-compute-node=enabled
kubectl label nodes osh openvswitch=enabled
kubectl label nodes osh linuxbridge=enabled
kubectl label nodes osh ceph-mon=enabled
kubectl label nodes osh ceph-osd=enabled
kubectl label nodes osh ceph-mds=enabled
kubectl label nodes osh ceph-rgw=enabled
kubectl label nodes osh ceph-mgr=enabled

# At this point can deploy osh scripts
# Note this is the developer scripts which work on a single node
# Eventually this can be moved to multinode/production
pushd openstack-helm
./tools/deployment/developer/common/020-setup-client.sh
./tools/deployment/developer/common/030-ingress.sh
./tools/deployment/developer/ceph/040-ceph.sh
./tools/deployment/developer/ceph/045-ceph-ns-activate.sh
./tools/deployment/developer/ceph/050-mariadb.sh
./tools/deployment/developer/ceph/060-rabbitmq.sh
./tools/deployment/developer/ceph/070-memcached.sh
./tools/deployment/developer/ceph/080-keystone.sh
./tools/deployment/developer/ceph/090-heat.sh
./tools/deployment/developer/ceph/100-horizon.sh
./tools/deployment/developer/ceph/110-ceph-radosgateway.sh
./tools/deployment/developer/ceph/120-glance.sh
./tools/deployment/developer/ceph/130-cinder.sh
./tools/deployment/developer/ceph/140-openvswitch.sh
./tools/deployment/developer/ceph/150-libvirt.sh
./tools/deployment/developer/ceph/160-compute-kit.sh
./tools/deployment/developer/ceph/170-setup-gateway.sh
./tools/deployment/developer/common/900-use-it.sh
export OS_CLOUD=openstack_helm
popd

# ./tools/deployment/multinode/020-ingress.sh
# ./tools/deployment/multinode/040-ceph-ns-activate.sh
# ./tools/deployment/multinode/050-mariadb.sh
# ./tools/deployment/multinode/060-rabbitmq.sh
# ./tools/deployment/multinode/070-memcached.sh
# ./tools/deployment/multinode/080-keystone.sh
# ./tools/deployment/multinode/090-ceph-radosgateway.sh
# ./tools/deployment/multinode/100-glance.sh
# ./tools/deployment/multinode/110-cinder.sh
# ./tools/deployment/multinode/120-openvswitch.sh
# ./tools/deployment/multinode/130-libvirt.sh
# ./tools/deployment/multinode/140-compute-kit.sh
# ./tools/deployment/multinode/150-heat.sh
# ./tools/deployment/multinode/160-barbican.sh

# * note additional cleanup

# * not needed
# ** Disable network manager
# https://github.com/openstack/openstack-helm-infra/blob/master/tools/images/kubeadm-aio/assets/opt/playbooks/roles/deploy-kubelet/tasks/setup-dns.yaml
# Disable network manager
# sudo stop network-manager
# echo "manual" | sudo tee /etc/init/network-manager.override
# *** hostname
# https://github.com/openstack/openstack-helm-infra/blob/master/tools/images/kubeadm-aio/assets/opt/playbooks/roles/deploy-kubelet/tasks/hostname.yaml
# Add:
# 127.0.0.1 localhost localhost.localdomain localhost4 localhost4.localdomain4
# ::1 localhost6 localhost6.localdomain6
# to /etc/hosts

# ** Other Installs
# sudo -H pip install python-openstackclient
# sudo -H pip install python-neutronclient
# sudo -H pip install python-cinderclient

# sudo apt install -y ebtables ethtool iproute2 iptables libmnl0 \
#                     libnfnetlink0 libwrap0 libxtables11 socat
# Prob more: https://github.com/openstack/openstack-helm-infra/blob/master/tools/images/kubeadm-aio/assets/opt/playbooks/roles/deploy-kubelet/tasks/kubelet.yaml
