#!/bin/bash
# Cleans Ceph from a k8s cluster

for NS in openstack ceph nfs libvirt; do
   helm ls --namespace $NS --short | xargs -r -L1 -P2 helm delete --purge
done

sudo systemctl stop kubelet
sudo systemctl disable kubelet

sudo docker ps -aq | xargs -r -L1 -P16 sudo docker rm -f

sudo rm -rf /var/lib/openstack-helm/*

sudo rm -rf /var/lib/nova/*
sudo rm -rf /var/lib/libvirt/*
sudo rm -rf /etc/libvirt/qemu/*

sudo findmnt --raw | awk '/^\/var\/lib\/kubelet\/pods/ { print $1 }' \| xargs -r -L1 -P16 sudo umount -f -l
