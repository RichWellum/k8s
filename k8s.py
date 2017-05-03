#!/usr/bin/env python
'''
Author: Rich Wellum (richwellum@gmail.com)

This is a tool to build a running Kubernetes Cluster on a single Bare Metal
server or a VM running on a server.

Initial supported state is a Centos 7 VM.

Configuration is done with kubeadm.

This relies heavily on my work on OpenStack kolla-kubernetes project and in
particular the Bare Metal Deployment Guide:

https://docs.openstack.org/developer/kolla-kubernetes/deployment-guide.html

Inputs:

1. build_vm   : Build a centos 7 VM to run k8s on
2. mgmt_int   : Name of the interface to be used for management operations
3. mgmt_ip    : IP Address of management interface
4. neutron_int: Name of the interface to be used for Neutron operations

TODO:

1. Will need a blueprint if adding this to community

Dependencies:

curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"

sudo python get-pip.py

psutil (sudo yum install gcc python-devel
        sudo pip install psutil)
docker (sudopip install docker)
'''

from __future__ import print_function
import sys
import os
import time
import subprocess
import argparse
from argparse import RawDescriptionHelpFormatter
import logging
import psutil
# import re


__author__ = 'Rich Wellum'
__copyright__ = 'Copyright 2017, Rich Wellum'
__license__ = ''
__version__ = '1.0.0'
__maintainer__ = 'Rich Wellum'
__email__ = 'rwellum@gmail.com'


# Telnet ports used to access IOS XR via socat
CONSOLE_PORT = 65000
AUX_PORT = 65001

# General-purpose retry interval and timeout value (10 minutes)
RETRY_INTERVAL = 5
TIMEOUT = 600

logger = logging.getLogger(__name__)


def set_logging():
    '''
    Set basic logging format.
    '''
    FORMAT = "[%(asctime)s.%(msecs)03d %(levelname)8s: %(funcName)20s:%(lineno)s] %(message)s"
    logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")


class AbortScriptException(Exception):
    """Abort the script and clean up before exiting."""


def parse_args():
    """Parse sys.argv and return args"""
    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description='A tool to create a working Kubernetes Cluster \n' +
        'on Bare Metal or a VM.',
        epilog='E.g.: k8s.py eth0 10.192.16.32 eth1\n')
    parser.add_argument('MGMT_INT',
                        help='Management Interface, E.g: eth0')
    parser.add_argument('MGMT_IP',
                        help='Management Interface IP Address, E.g: 10.240.83.111')
    parser.add_argument('NEUTRON_INT',
                        help='Neutron Interface, E.g: eth1')
    parser.add_argument('-c', '--cleanup', action='store_true',
                        help='Cleanup existing Kubernetes cluster before creating a new one')
    parser.add_argument('-k8s', '--kubernetes', action='store_true',
                        help='Stop after bringing up kubernetes.')
    # parser.add_argument('-l,', '--cloud', type=int, default=3,
    #                     help='optionally change cloud network config files from default(3)')
    parser.add_argument('-v', '--verbose',
                        action='store_const', const=logging.DEBUG,
                        default=logging.INFO, help='turn on verbose messages')

    return parser.parse_args()


def run(cmd, hide_error=False, cont_on_error=False):
    '''
    Run command to execute CLI and catch errors and display them whether
    in verbose mode or not.

    Allow the ability to hide errors and also to continue on errors.
    '''
    s_cmd = ' '.join(cmd)
    logger.debug("Command: '%s'\n", s_cmd)

    output = subprocess.Popen(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    tup_output = output.communicate()

    if output.returncode != 0:
        logger.debug('Command failed with code %d:', output.returncode)
    else:
        logger.debug('Command succeeded with code %d:', output.returncode)

    logger.debug('Output for: ' + s_cmd)
    logger.debug(tup_output[0])

    if not hide_error and 0 != output.returncode:
        logger.error('Error output for: ' + s_cmd)
        logger.error(tup_output[1])
        if not cont_on_error:
            raise AbortScriptException(
                "Command '{0}' failed with return code {1}".format(
                    s_cmd, output.returncode))
        logger.debug('Continuing despite error %d', output.returncode)

    return tup_output[0]


def start_process(args):
    '''
    Start vboxheadless process
    '''
    logger.debug('args: %s', args)
    with open(os.devnull, 'w') as fp:
        subprocess.Popen((args), stdout=fp)
    time.sleep(2)


def pause_to_debug():
    """Pause the script for manual debugging of the VM before continuing."""
    print("Pause before debug")
    raw_input("Press Enter to continue.")


def curl(*args):
    curl_path = '/usr/bin/curl'
    curl_list = [curl_path]
    for arg in args:
        curl_list.append(arg)
    curl_result = subprocess.Popen(
        curl_list,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE).communicate()[0]
    return curl_result


def create_k8s_repo():
    """Create a k8s repository file"""
    name = './kubernetes.repo'
    repo = '/etc/yum.repos.d/kubernetes.repo'
    with open(name, "w") as w:
        w.write("""\
[kubernetes]
name=Kubernetes
baseurl=http://yum.kubernetes.io/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
""")
    run(['sudo', 'mv', './kubernetes.repo', repo])


def k8s_wait_for_pods():
    """Wait for basic k8s to come up"""

    TIMEOUT = 350  # Give k8s 350s to come up
    RETRY_INTERVAL = 10

    elapsed_time = 0
    while True:
        pod_status = run(['kubectl', 'get', 'pods', '--all-namespaces'])
        nlines = len(pod_status.splitlines())
        if nlines - 1 == 6:
            print('Kubernetes - all pods %s/6 are started, continuing' % (nlines - 1))
            p = subprocess.Popen('kubectl get pods --all-namespaces',
                                 stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            print('%s' % output)
            break
        elif elapsed_time < TIMEOUT:
            if (nlines - 1) < 0:
                cnt = 0
            else:
                cnt = nlines - 1

            if elapsed_time is not 0:
                print("Kubernetes - not started after %d seconds, pods %s:6 - "
                      "sleep %d seconds and retry"
                      % (elapsed_time, cnt, RETRY_INTERVAL))
            time.sleep(RETRY_INTERVAL)
            elapsed_time = elapsed_time + RETRY_INTERVAL
            continue
        else:
            # Dump verbose output in case it helps...
            print(pod_status)
            raise AbortScriptException(
                "k8s did not come up after {0} seconds!"
                .format(elapsed_time))


def k8s_wait_for_running(number):
    """Wait for k8s pods to be in running status

    number is the minimum number of 'Running' pods expected"""

    TIMEOUT = 350  # Give k8s 350s to come up
    RETRY_INTERVAL = 10

    print('Waiting for %s pods to be in Running state' % number)
    elapsed_time = 0
    while True:
        p = subprocess.Popen('kubectl get pods --all-namespaces | grep "Running" | wc -l',
                             stdout=subprocess.PIPE, shell=True)
        (running, err) = p.communicate()
        p.wait()

        if int(running) >= number:
            print('Kubernetes - all Running pods %s:%s' % (int(running), number))
            p = subprocess.Popen('kubectl get pods --all-namespaces',
                                 stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            print('%s' % output)

            break
        elif elapsed_time < TIMEOUT:
            print('Kubernetes - Running pods %s:%s - sleep %d seconds and retry'
                  % (int(running), number, RETRY_INTERVAL))
            time.sleep(RETRY_INTERVAL)
            elapsed_time = elapsed_time + RETRY_INTERVAL
            continue
        else:
            # Dump verbose output in case it helps...
            print(int(running))
            raise AbortScriptException(
                "Kubernetes did not come up after {0} seconds!"
                .format(elapsed_time))


# def k8s_check_dns():
#     kubectl run - i - t $(uuidgen) - -image = busybox - -restart = Never
#     p = subprocess.Popen('kubectl get pods --all-namespaces',
#                                  stdout=subprocess.PIPE, shell=True)
#             (output, err) = p.communicate()
#             print('%s' % output)

def k8s_kolla_update_rbac():
    """..."""
    print("Overide default RBAC settings")
    name = '/tmp/rbac'
    with open(name, "w") as w:
        w.write("""\
apiVersion: rbac.authorization.k8s.io/v1alpha1
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
""")

    run(['kubectl', 'update', '-f', '/tmp/rbac'])


def k8s_kolla_install_deploy_helm():
    print("Install and deploy Helm")
    # answer = curl(
    #     '-L',
    #     'https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get',
    #     '-o', '/tmp/get_helm.sh')
    # print(answer)
    url = 'https://storage.googleapis.com/kubernetes-helm/helm-v2.3.0-linux-amd64.tar.gz'
    answer = curl('-sSL',
                  url,
                  '-o',
                  '/tmp/helm-v2.3.0-linux-amd64.tar.gz')
    print(answer)
    run(['tar', '-xvzf', '/tmp/helm-v2.3.0-linux-amd64.tar.gz', '-C' '/tmp'])
    run(['sudo', 'mv', '/tmp/helm', '/usr/local/bin/helm'])
    # run(['chmod', '700', '/tmp/get_helm.sh'])
    pause_to_debug()
    subprocess.call('helm init')


def main():
    """Main function."""
    args = parse_args()

    if args.cleanup is True:
        print("Cleaning up existing Kubernetes Cluster. YMMV.")
        run(['sudo', 'kubeadm', 'reset'])

    print(args.MGMT_INT, args.MGMT_IP, args.NEUTRON_INT)

    set_logging()
    logger.setLevel(level=args.verbose)

    try:
        print('Turn off SELinux')
        run(['sudo', 'setenforce', '0'])
        run(['sudo', 'sed', '-i', 's/enforcing/permissive/g', '/etc/selinux/config'])

        print('Turn off Firewalld if running')
        PROCNAME = 'firewalld'
        for proc in psutil.process_iter():
            if PROCNAME in proc.name():
                print('Found %s, Stopping and Disabling firewalld' % proc.name())
                run(['sudo', 'systemctl', 'stop', 'firewalld'])
                run(['sudo', 'systemctl', 'disable', 'firewalld'])

        print('Creating kubernetes repo')
        create_k8s_repo()
        print('Installing k8s 1.6.1 or later - please wait')
        subprocess.check_output(
            'sudo yum install -y docker ebtables kubeadm kubectl kubelet kubernetes-cni git gcc xterm', shell=True)
        print('Enable the correct cgroup driver and disable CRI')
        run(['sudo', 'systemctl', 'enable', 'docker'])
        run(['sudo', 'systemctl', 'start', 'docker'])

        # Looks like note needed?
        # CGROUP_DRIVER = subprocess.check_output(
        #     'sudo docker info | grep "Cgroup Driver" | awk "{print $3}"', shell=True)

        # if 'systemd' in CGROUP_DRIVER:
        #     # Todo: search and use
        #     CGROUP_DRIVER = 'systemd'

        run(['sudo', 'cp', '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf', '/tmp'])
        run(['sudo', 'chmod', '777', '/tmp/10-kubeadm.conf'])
        # Latest version of canal doesn't need this
        # run(['sudo', 'sed', '-i', 's|KUBELET_KUBECONFIG_ARGS=|KUBELET_KUBECONFIG_ARGS=--cgroup-driver=$CGROUP_DRIVER --enable-cri=false |g',
        #      '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf'])

        print('Setup the DNS server with the service CIDR')
        run(['sudo', 'sed', '-i', 's/10.96.0.10/10.3.3.10/g', '/tmp/10-kubeadm.conf'])
        run(['sudo', 'mv', '/tmp/10-kubeadm.conf',
             '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf'])

        print('Reload the hand-modified service files')
        run(['sudo', 'systemctl', 'daemon-reload'])

        print('Stop kubelet if it is running')
        run(['sudo', 'systemctl', 'stop', 'kubelet'])

        print('Enable and start docker and kubelet')
        run(['sudo', 'systemctl', 'enable', 'kubelet'])
        run(['sudo', 'systemctl', 'start', 'kubelet'])

        print('Fix iptables')
        run(['sudo', 'cp', '/etc/sysctl.conf', '/tmp'])
        run(['sudo', 'chmod', '777', '/tmp/sysctl.conf'])

        with open('/tmp/sysctl.conf', 'a') as myfile:
            myfile.write('net.bridge.bridge-nf-call-ip6tables=1' + '\n')
            myfile.write('net.bridge.bridge-nf-call-iptables=1')
        run(['sudo', 'mv', '/tmp/sysctl.conf', '/etc/sysctl.conf'])
        run(['sudo', 'sysctl', '-p'])

        print('Deploying Kubernetes with kubeadm')
        # kubeadm init --skip-preflight-checks --service-cidr 172.16.128.0/24 --pod-network-cidr 172.16.132.0/22 \
        # --apiserver-advertise-address $(cat /etc/nodepool/primary_node_private) | tee /tmp/kubeout
        # grep 'kubeadm join --token' /tmp/kubeout | awk '{print $4}' > /etc/kubernetes/token.txt
        run(['sudo', 'kubeadm', 'init', '--pod-network-cidr=10.1.0.0/16',
             '--service-cidr=10.3.3.0/24', '--skip-preflight-checks'])

        print('Load the kubeadm credentials into the system')
        home = os.environ['HOME']
        kube = os.path.join(home, '.kube')
        config = os.path.join(kube, 'config')

        if not os.path.exists(kube):
            os.makedirs(kube)
        run(['sudo', 'cp', '/etc/kubernetes/admin.conf', config])
        run(['sudo', 'chmod', '777', kube])
        subprocess.call('sudo -H chown $(id -u):$(id -g) $HOME/.kube/config',
                        shell=True)

        # Wait for all pods to be launched
        k8s_wait_for_pods()
        k8s_wait_for_running(5)

        print('Deploy the Canal CNI driver')
        answer = curl(
            '-L',
            'https://raw.githubusercontent.com/projectcalico/canal/master/k8s-install/1.6/rbac.yaml',
            '-o', '/tmp/rbac.yaml')
        print(answer)
        run(['kubectl', 'create', '-f', '/tmp/rbac.yaml'])

        answer = curl(
            '-L',
            'https://raw.githubusercontent.com/projectcalico/canal/master/k8s-install/1.6/canal.yaml',
            '-o', '/tmp/canal.yaml')
        print(answer)
        run(['sudo', 'chmod', '777', '/tmp/canal.yaml'])
        run(['sudo', 'sed', '-i', 's@192.168.0.0/16@10.1.0.0/16@', '/tmp/canal.yaml'])
        run(['sudo', 'sed', '-i', 's@10.96.232.136@10.3.3.100@', '/tmp/canal.yaml'])
        run(['kubectl', 'create', '-f', '/tmp/canal.yaml'])

        k8s_wait_for_running(7)

        # todo: nslookup check
        if args.kubernetes is True:
            print("Kubernetes Cluster is running and healthy and you do not wish to install kolla")
            sys.exit(1)

        k8s_kolla_update_rbac()
        k8s_kolla_install_deploy_helm()
        k8s_wait_for_running(8)

    except Exception:
        print('Exception caught:')
        print(sys.exc_info())
        raise


if __name__ == '__main__':
    main()
