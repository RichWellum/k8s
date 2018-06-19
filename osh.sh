#!/bin/bash

# To be converted to python
sudo -v
rm -rf openstack-helm*
git clone https://git.openstack.org/openstack/openstack-helm-infra.git
git clone https://git.openstack.org/openstack/openstack-helm.git

# Add: nameserver 10.96.0.10 - to resolv.conf
# Add: options ndots:5 timeout:1 attempts:1
sudo apt install ceph-common -y

helm repo add local http://localhost:8879/charts

cd ../openstack-helm-infra
make clean
git pull
make all
cd ../openstack-helm
make clean
git pull
make all

helm serve &

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
