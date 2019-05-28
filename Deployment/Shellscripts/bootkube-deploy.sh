#!/bin/bash
# BootKube Deployment (FINAL):

## NEW INSTALLATIONS:
echo "Updating and Installing base tools"
sudo apt-get update && sudo apt-get upgrade -y && \
    sudo apt install -y docker.io ethtool traceroute git lldpd socat apparmor

### PREPARE THE ENVIRONMENT:
echo "Prepare the environment"
export CNI_VERSION=v0.6.0                    ### CNI VERSION                 ###
export HELM_VERSION=v2.11.0                  ### HELM VERSION                ###
export BOOTKUBE_VERSION=v0.14.0              ### BOOTKUBE VERSION            ###
                                             ### KUBERNETES VERSION          ###
export KUBERNETES_VERSION=$(curl -sSL https://dl.k8s.io/release/stable.txt)
# TODO: Resolve this as this is Ubuntu
#export KUBE_HW='ens2'                        ### MODIFY FOR YOUR ENVIRONMENT ###
export KUBE_HW=$(ip a | grep ens | grep inet | awk '{print $7}')
export KUBE_IP=$(ip a s dev $KUBE_HW | awk '/inet /{gsub("/.*", "");print $2}')
echo "Kubernetes Endpoint: $KUBE_HW:$KUBE_IP"

#export NSERVER01='10.3.0.10'                 ### DO NOT MODIFY FOR CEPH PV   ###
#export NSERVER01=$KUBE_IP       use google 2nd              ### MODIFY FOR YOUR ENVIRONMENT ###
export NSERVER01='8.8.4.4'                   ### MODIFY FOR YOUR ENVIRONMENT ###
export NSERVER02='8.8.8.8'                  ### MODIFY FOR YOUR ENVIRONMENT ###

export NSEARCH01='svc.cluster.local'        ### MODIFY FOR YOUR ENVIRONMENT ###
#export NSEARCH02='bootkube-deploy.sh'       ### MODIFY FOR YOUR ENVIRONMENT ###

# TODO - replace this
export KUBE_IMAGE='nzoueidi/hyperkube-amd64' ### MODIFY FOR YOUR ENVIRONMENT ###

# Turn swap off
echo "Turn Swap off"
sudo swapoff -a
sudo modprobe br_netfilter

### PREPARE: /etc/resolv.conf
# echo "Prepare resolv.conf"
# sudo mv /etc/resolv.conf /etc/resolveconf
# sudo -E bash -c "cat <<EOF > /etc/resolv.conf
# nameserver $NSERVER01
# nameserver $NSERVER02
# nameserver $NSERVER03
# search $NSEARCH01 $NSEARCH02
# EOF"

# backup
echo "Prepare resolv.conf"
sudo mv /etc/resolv.conf /etc/resolveconf
sudo -E bash -c "cat <<EOF > /etc/resolv.conf
nameserver $NSERVER01
nameserver $NSERVER02
search $NSEARCH01
EOF"
cat /etc/resolv.conf

### PREPARE: /etc/hosts:
echo "Prepare /etc/hosts"
sudo cp /etc/hosts /etc/hosts.save
#sudo -E bash -c 'echo '$KUBE_IP' '$NSEARCH02' kubernetes loadbalancer.'$NSEARCH02' '$HOSTNAME' '$HOSTNAME'.'$NSEARCH02' >> /etc/hosts'
sudo -E bash -c 'echo 127.0.0.1 localhost > /etc/hosts'
sudo -E bash -c 'echo '$KUBE_IP' kubernetes  '$HOSTNAME' '$HOSTNAME'.'$NSEARCH01' >> /etc/hosts'
sudo -E bash -c 'echo '' >> /etc/hosts'
cat /etc/hosts

### PREPARE: /etc/systemd/system/kubelet.service
echo "Prepare Kubernetes"
sudo -E bash -c 'cat <<EOF > /etc/systemd/system/kubelet.service
[Unit]
Description=Kubernetes Kubelet
Documentation=https://kubernetes.io/docs/admin/kubelet/
[Service]
ExecStartPre=/bin/mkdir -p /etc/kubernetes/manifests
ExecStart=/usr/local/bin/kubelet \\
    --allow-privileged \\
    --cluster_domain=cluster.local \\
    --cluster_dns='10.96.0.10' \\
    --cni-conf-dir=/etc/cni/net.d \\
    --exit-on-lock-contention \\
    --hostname-override='$HOSTNAME.$NSEARCH01' \\
    --kubeconfig=/etc/kubernetes/kubeconfig \\
    --lock-file=/var/run/lock/kubelet.lock \\
    --minimum-container-ttl-duration=3m0s \\
    --node-labels=node-role.kubernetes.io/master \\
    --node-ip='$KUBE_IP' \\
    --network-plugin=cni \\
    --pod-manifest-path=/etc/kubernetes/manifests \\
    --register-with-taints=node-role.kubernetes.io/master=:NoSchedule \\
    --fail-swap-on=false \\
    --cgroup-driver=cgroupfs \\
    --v=2
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF'
cat /etc/systemd/system/kubelet.service

#Changes:
# --require-kubeconfig \\
# --hostname-override='$KUBE_IP' \\
# --node-labels= \\
# --cluster_dns='$NSERVER02','$NSERVER03','$NSERVER01' \\
# --cni-bin-dir=/opt/cni/bin \\
#Restart=on-failure

### DOWNLOAD BINARIES
echo "Download Binaries"

### DOWNLOAD: bootkube
wget https://github.com/kubernetes-incubator/bootkube/releases/download/$BOOTKUBE_VERSION/bootkube.tar.gz
tar zxvf bootkube.tar.gz
sudo chmod +x bin/linux/bootkube
sudo cp bin/linux/bootkube /usr/local/bin/

### DOWNLOAD: kubectl, kubeadm and kubelet
wget https://storage.googleapis.com/kubernetes-release/release/$KUBERNETES_VERSION/bin/linux/amd64/{kubeadm,kubelet,kubectl}
sudo chmod +x kubectl
sudo mv kubectl /usr/local/bin/
sudo chmod +x kubelet
sudo mv kubelet /usr/local/bin/

### DOWNLOAD: cni
wget https://github.com/containernetworking/cni/releases/download/$CNI_VERSION/cni-amd64-$CNI_VERSION.tgz
sudo mkdir -p /opt/cni/bin
sudo tar -xf cni-amd64-$CNI_VERSION.tgz -C /opt/cni/bin/

### DOWNLOAD: helm
wget -O /tmp/helm-$HELM_VERSION-linux-amd64.tar.gz https://storage.googleapis.com/kubernetes-helm/helm-$HELM_VERSION-linux-amd64.tar.gz
tar zxvf /tmp/helm-$HELM_VERSION-linux-amd64.tar.gz -C /tmp/
chmod +x /tmp/linux-amd64/helm
sudo mv /tmp/linux-amd64/helm /usr/local/bin/
sudo rm -rf /tmp/linux-amd64

### CLEANUP:
sudo rm -rf /home/$USER/cni-amd64-$CNI_VERSION.tgz
sudo rm -rf /home/$USER/bootkube.tar.gz
sudo rm -rf /home/$USER/bin

# echo "Stopping here for manual render"
# exit 1

### RENDER ASSETS:
echo "Render Bootkube assets"
# Experimental self hosted is gone I think
# sudo /usr/bin/docker run -v /home/ubuntu:/home/ubuntu quay.io/coreos/bootkube:$BOOTKUBE_VERSION
# /bootkube render --asset-dir=/home/ubuntu/.bootkube --experimental-self-hosted-etcd
# --etcd-servers=http://10.3.0.15:12379 --api-servers=https://kubernetes:6443
sudo /usr/bin/docker run -v \
     /home/$USER:/home/$USER \
     quay.io/coreos/bootkube:$BOOTKUBE_VERSION \
     /bootkube render \
     --asset-dir=/home/$USER/.bootkube \
     --etcd-servers=http://10.3.0.15:12379 \
     --api-servers=https://kubernetes:6443
# sudo /usr/bin/docker run -v /home/$USER:/home/$USER quay.io/coreos/bootkube:$BOOTKUBE_VERSION
# /bootkube render --asset-dir=assets --api-servers=https://192.168.3.120:6443
# --etcd-servers=http://192.168.3.120:2379 --api-server-alt-names=IP=192.168.3.120

sudo rm -rf /home/$USER/.bootkube/manifests/kube-flannel*

### REQUIRED FOR CEPH/OPTIONAL ALL OTHERS:
# sudo grep -rl "quay.io/coreos/hyperkube:$KUBERNETES_VERSION_coreos.0" /home/$USER/.bootkube/ | sudo xargs sed -i 's|quay.io/coreos/hyperkube:$KUBERNETES_VERSION_coreos.0|$KUBE_IMAGE:$KUBERNETES_VERSION|g'
sudo grep -rl quay.io/coreos/hyperkube:$KUBERNETES_VERSION'_coreos.0' /home/$USER/.bootkube/ | sudo xargs sed -i "s|quay.io/coreos/hyperkube:"$KUBERNETES_VERSION"_coreos.0|quay.io/"$KUBE_IMAGE":"$KUBERNETES_VERSION"|g"

### DEPLOY KUBERNETES SELF-HOSTED CLUSTER:
echo "Deploy Bootkube Self-Hosted Cluster"
sudo systemctl daemon-reload
sudo systemctl restart kubelet.service
sudo cp /home/$USER/.bootkube/auth/kubeconfig /etc/kubernetes/
sudo cp -a /home/$USER/.bootkube/* /etc/kubernetes/
sudo mkdir -p /home/$USER/.kube
sudo cp /etc/kubernetes/kubeconfig /home/$USER/.kube/config
sudo chmod 644 /home/$USER/.kube/config
# DEBUG #sudo touch /home/ubuntu/.bootkube/bootkube-up.log
nohup sudo bash -c 'bootkube start --asset-dir=/home/$USER/.bootkube &>/dev/null &'

### WAIT FOR KUBERNETES ENVIRONMENT TO COME UP:
function echo_green {
  echo -e "${GREEN}$1"; tput sgr0
}

echo -e -n "Waiting for master components to start..."
while true; do
  running_count=$(sudo kubectl get pods -n kube-system --no-headers 2>/dev/null | grep "Running" | wc -l)
  ### Expect 4 bootstrap components for a truly "Ready" state: etcd, apiserver, controller, and scheduler:
  if [ "$running_count" -ge 4 ]; then
    break
  fi
  echo -n "."
  sleep 1
done
echo_green "SUCCESS"
echo_green "Cluster created!"
echo ""
sudo kubectl cluster-info

sleep 10

### WAIT FOR KUBERNETES API TO COME UP CLEANLY, THEN APPLY FOLLOWING LABELS AND MANIFESTS:
echo "Apply labels"
sudo kubectl --kubeconfig=/etc/kubernetes/kubeconfig label node --all node-role.kubernetes.io/canal-node=true
sudo kubectl --kubeconfig=/etc/kubernetes/kubeconfig label node --all node-role.kubernetes.io/master="" --overwrite
sudo kubectl --kubeconfig=/etc/kubernetes/kubeconfig apply -f URL/canal-etcd.yaml
sudo kubectl --kubeconfig=/etc/kubernetes/kubeconfig apply -f URL/canal.yaml
sudo kubectl --kubeconfig=/etc/kubernetes/kubeconfig apply -f URL/calico-cfg.yaml

printf "\nCOMPLETE!\n"
