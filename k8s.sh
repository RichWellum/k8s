#!/bin/bash
# bash version of k8s.sh to debug k8s.py :(

sudo yum update -y

sudo setenforce 0
sudo sed -i s/enforcing/permissive/g /etc/selinux/config # needed?
sudo sed -i --follow-symlinks 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/sysconfig/selinux

sudo swapoff -a

# We must also ensure that swap isn't re-enabled during a reboot on each server. Open up the /etc/fstab and comment out the swap entry like this:

# /dev/mapper/centos-swap swap swap defaults 0 0

sudo modprobe br_netfilter

sudo echo '1' > /proc/sys/net/bridge/bridge-nf-call-iptables #needs real su

# not sure if needed?
sudo yum install -y qemu epel-release bridge-utils \
     python-pip python-devel libffi-devel gcc \
     openssl-devel sshpass crudini jq ansible curl lvm2

# not sure if needed
sudo yum install -y ntp
sudo systemctl enable ntpd.service
sudo systemctl start ntpd.service

sudo systemctl stop firewalld
sudo systemctl disable firewalld

sudo cat << EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
        https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF

sudo yum install -y kubelet kubeadm kubectl
# 'ebtables kubelet kubeadm kubectl kubernetes-cni

sudo yum remove -y docker docker-common docker-selinux docker-engine
sudo yum install -y yum-utils device-mapper-persistent-data lvm2
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce

sudo sed -i 's/cgroup-driver=systemd/cgroups-driver=cgroupfs/g' /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
sudo systemctl daemon-reload
sudo systemctl stop kubelet
sudo systemctl start kubelet
sudo systemctl enable kubelet.service

sudo systemctl enable docker
sudo systemctl start docker

sudo cp /etc/systemd/system/kubelet.service.d/10-kubeadm.conf /tmp
sudo chmod 777 /tmp/10-kubeadm.conf
sudo sed -i s/10.96.0.10/10.3.3.10/g /tmp/10-kubeadm.conf
sudo echo Environment="KUBELET_CGROUP_ARGS=--cgroup-driver=systemd" >> \
     /tmp/10-kubeadm.conf
sudo echo Environment="KUBELET_EXTRA_ARGS=--fail-swap-on=false" >> \
     /tmp/10-kubeadm.conf
sudo echo Environment="KUBELET_DOS_ARGS=--runtime-cgroups=/systemd/system.slice \
     --kubelet-cgroups=/systemd/system.slice --hostname-override=$(hostname) \
     --fail-swap-on=false" >> /tmp/10-kubeadm.conf
sudo mv /tmp/10-kubeadm.conf /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
sudo sysctl -p

sudo kubeadm init --pod-network-cidr=10.1.0.0/16 --service-cidr=10.3.3.0/24 --ignore-preflight-errors=all

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

#Google this
# kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')"

# Don't allow Weave Net to crunch ip's used by k8s
# name='/tmp/ipalloc.txt'
# cat << EOF > /tmp/ipalloc.tx
# - name: IPALLOC_RANGE
#   value: 10.0.0.0/16
# EOF
# chmod 777 /tmp/ipalloc.txt /tmp/weave.yaml
# sed -i '/fieldPath: spec.nodeName/ r /tmp/ipalloc.txt' /tmp/weave.yaml

# kubectl apply -f /tmp/weave.yaml

# Try canal
curl -L https://docs.projectcalico.org/v3.1/getting-started \
        /kubernetes/installation/hosted/canal/rbac.yaml \
        -o /tmp/rbac.yaml
kubectl create -f /tmp/rbac.yaml

curl -L https://docs.projectcalico.org/v3.1/getting-started \
        /kubernetes/installation/hosted/canal/canal.yaml \
        -o /tmp/canal.yaml
sudo chmod 777 /tmp/canal.yaml
sudo sed -i s@10.244.0.0/16@10.1.0.0/16@ /tmp/canal.yaml
kubectl create -f /tmp/canal.yaml

kubectl taint nodes --all=true node-role.kubernetes.io/master:NoSchedule-

sudo cat << EOF > /tmp/rbac
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: Group
  name: system:masters
- kind: Group
  name: system:authenticated
- kind: Group
  name: system:unauthenticated
EOF

kubectl apply -f /tmp/rbac.yaml
