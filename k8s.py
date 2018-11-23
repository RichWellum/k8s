#!/usr/bin/env python

'''
k8s.py - Simple Python Kubernetes wrapper around kubeadm

Purpose
=======
Setup environment for running kubernetes, install a simple cluster with
kubeadm.

Features
========
1. Supports Centos and Ubuntu, Flatcar and CoreOS is in alpha.

2. Requires just a VM with one external NIC.

3. Easy on the eye output, with optional verbose mode for more information.

4. Destroy previous deployment with -d option

5. Option to create a kubernetes minion to add to existing deployment.

Host machine requirements
=========================

The host machine must satisfy the following minimum requirements:

- 1 network interfaces
- 2GB min, 4GB+ preferred RAM
- 20G min, 40GB+ preferred disk space
- 2 CPU's Min, 4+ preferred CPU's
- Root access to the deployment host machine

User Recomendations
=================
- Create an admin user - don't run from root
- Disable timeouts

Add user (centos/ubuntu)
-------------------------------------
Centos
       adduser stack
       passwd stack
       usermod -aG wheel stack

Ubuntu
       adduser stack
       usermod -aG sudo stack

Both
       visudo:
       stack  ALL=(ALL) NOPASSWD: ALL
       Defaults    timestamp_timeout=-1

Recomendations
==============

Alt way to run:

curl https://raw.githubusercontent.com/RichWellum/k8s/master/k8s.py | python -

Proxy
====

To handle a proxy, add management ip (ip a) to the no_proxy in
/etc/profile.d/nsnproxy.sh

Flatcar / Coreos
================
Flatcare and Coreos is still experimental

See:
https://gist.github.com/kevashcraft/5aa85f44634c37a9ee05dde7e83ac7e2#install-kubernetes

Follow these steps first:

sudo su

https://github.com/judexzhu/Install-Python-on-CoreOs

wget -qO- https://raw.githubusercontent.com/judexzhu/Install-Python-on-\
CoreOs/master/install-python.sh | bash

cat > ~/.bashrc << EOF
export PATH="/opt/bin:$PATH"
EOF
source ~/.bashrc

'''

from __future__ import print_function
import argparse
from argparse import RawDescriptionHelpFormatter
import logging
import os
import platform
import re
import subprocess
import sys
import tarfile
import time
start_time = time.time()

logger = logging.getLogger(__name__)

# Nasty globals but used universally
global PROGRESS
PROGRESS = 0

global K8S_FINAL_PROGRESS
K8S_FINAL_PROGRESS = 1

global K8S_DESTROY_PROGRESS
K8S_DESTROY_PROGRESS = 0

# Store the kubeadm join command, and display to user at end of deployment
global JOIN_CMD


def set_logging():
    '''Set basic logging format.'''

    FORMAT = "[%(asctime)s.%(msecs)03d %(levelname)8s: "\
        "%(funcName)20s:%(lineno)s] %(message)s"
    logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")


class AbortScriptException(Exception):
    '''Abort the script and clean up before exiting.'''


def parse_args():
    '''Parse sys.argv and return args'''

    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description='This tool provides a method to deploy a Kubernetes '
        'Cluster on bare metal servers or virtual machines.\nVirtual '
        'machines supported are Ubuntu and Centos.\n'
        'The host machine must satisfy the following minimum requirements:\n'
        '- 1 network interfaces\n'
        '- 4GB min, 8GB preferred - main memory\n'
        '- 20G min, 40GB preferred - disk space\n'
        '- 2 CPUs Min, 4 preferred - CPUs\n'
        'Root access to the deployment host machine is required.',
        epilog='E.g.: python k8s.py -c\n')
    parser.add_argument('-hv', '--helm_version', type=str, default='2.11.0',
                        help='Specify a different helm version to the '
                        'latest')
    parser.add_argument('-m', '--minion', action='store_true',
                        help='set up a node to be used as a minion '
                        'to be JOINed to a master')
    parser.add_argument('-v', '--verbose', action='store_const',
                        const=logging.DEBUG, default=logging.INFO,
                        help='turn on verbose messages, commands and outputs')
    parser.add_argument('-c', '--commmands', action='store_true',
                        help='turn on commands used')
    parser.add_argument('-d', '--destroy', action='store_true',
                        help='destroy existing Kubernetes cluster '
                        'before creating a new one.')

    return parser.parse_args()


def run_shell(args, cmd):
    '''Run a shell command and return the output

    Print the output and errors if debug is enabled
    Not using logger.debug as a bit noisy for this info
    '''
    debug = False
    if args.verbose == 10:  # Hack - debug enabled
        debug = True

    if debug is True or args.commmands:
        print('  CMD: "%s"' % str(cmd))

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    out, err = p.communicate()

    out = out.rstrip()
    err = err.rstrip()

    if debug is True:
        if str(out) is not '0' and str(out) is not '1' and out:
            print('  Shell STDOUT output:')
            print()
            print(out)
            print()
        if err:
            print('  Shell STDERR output:')
            print()
            print(err)
            print()
    return(out)


def untar(fname):
    '''Untar a tarred and compressed file'''

    if (fname.endswith("tar.gz")):
        tar = tarfile.open(fname, "r:gz")
        tar.extractall()
        tar.close()
    elif (fname.endswith("tar")):
        tar = tarfile.open(fname, "r:")
        tar.extractall()
        tar.close()


def banner(description):
    '''Display a bannerized print'''

    banner = len(description)
    if banner > 100:
        banner = 100

    # First banner
    print('\n')
    for c in range(banner):
        print('*', end='')

    # Add description
    print('\n%s' % description)

    # Final banner
    for c in range(banner):
        print('*', end='')
    print('\n')


def curl(*args):
    '''Use curl to retrieve a file from a URI'''

    curl_path = '/usr/bin/curl'
    curl_list = [curl_path]
    for arg in args:
        curl_list.append(arg)
    curl_result = subprocess.Popen(
        curl_list,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE).communicate()[0]
    return curl_result


def linux_ver(args):
    '''Determine Linux version'''

    find_os = platform.linux_distribution()
    if re.search('Centos', find_os[0], re.IGNORECASE):
        linux = 'centos'
    elif re.search('Ubuntu', find_os[0], re.IGNORECASE):
        linux = 'ubuntu'
    else:
        find_os = run_shell(args, "cat /proc/version | cut -d' ' -f3")
        if re.search('flatcar', find_os, re.IGNORECASE):
            linux = 'container'
        elif re.search('coreos', find_os, re.IGNORECASE):
            linux = 'container'
        else:
            print('Linux "%s" is not supported yet' % find_os[0])
            sys.exit(1)

    return(linux)


def linux_ver_det():
    '''Determine detailed Linux version - Ubuntu or Centos

    Return OS, OS Versions
    '''

    return(platform.linux_distribution()[0],
           platform.linux_distribution()[1],
           platform.linux_distribution()[2])


def k8s_ver(args):
    '''Display kubernetes version'''

    oldstr = run_shell(
        args,
        "kubectl version | grep 'Client Version' "
        "| awk '{print $5}' | cut -d '\"' -f2")
    return(oldstr)
    newstr = oldstr.replace(",", "")

    return(newstr.rstrip())


def docker_ver(args):
    '''Display Docker version'''

    oldstr = run_shell(args, "docker --version | awk '{print $3}'")
    newstr = oldstr.replace(",", "")

    return(newstr.rstrip())


def helm_version(args, str):
    '''A Dictionary of tools and their versions

    Defaults are populated by tested well known versions.

    User can then overide each individual tool.

    Return a Version for a string.

    Note that currently this is just for helm.
    '''

    tools = ["helm"]

    # This should match up with the defaults set in parse_args
    #           helm
    versions = ["2.11.0"]

    tools_dict = {}
    # Generate dictionary
    for i in range(len(tools)):
        tools_dict[tools[i]] = versions[i]

    # Now overide based on user input - first
    if tools_dict["helm"] is not args.helm_version:
        tools_dict["helm"] = args.helm_version

    return(tools_dict[str])


def print_versions(args):
    '''Print out lots of information

    Tool versions, networking, user options and more
    '''

    print('\n  Linux Host Info:')
    os, os_ver, os_ver_s = linux_ver_det()
    print('    OS:                %s' % os)
    print('    OS version:        %s' % os_ver)
    print('    OS version str:    %s' % os_ver_s)

    print('\n  Networking Info:')
    print('    CNI/SDN:            Weave')

    print('\n  Tool Versions:')
    print('    Docker version:     %s' % docker_ver(args))
    print('    Helm version:       %s' % helm_version(args, 'helm'))
    print('    K8s version:        %s' % k8s_ver(args).rstrip())
    print('\n')
    time.sleep(2)


def k8s_create_repo(args):
    '''Create a k8s repository file'''

    if linux_ver(args) == 'centos':
        name = './kubernetes.repo'
        repo = '/etc/yum.repos.d/kubernetes.repo'
        with open(name, "w") as w:
            w.write("""\
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg

exclude=kube*
""")
        # todo: add -H to all sudo's see if it works in both envs
        run_shell(args, 'sudo mv ./kubernetes.repo %s' % repo)
    elif linux_ver(args) == 'ubuntu':
        run_shell(args,
                  'curl -s https://packages.cloud.google.com'
                  '/apt/doc/apt-key.gpg '
                  '| sudo -E apt-key add -')
        name = './kubernetes.list'
        repo = '/etc/apt/sources.list.d/kubernetes.list'
        with open(name, "w") as w:
            w.write("""\
deb http://apt.kubernetes.io/ kubernetes-xenial main
""")
        run_shell(args, 'sudo mv ./kubernetes.list %s' % repo)
        run_shell(args, 'sudo apt-get update')


def k8s_wait_for_kube_system(args):
    '''Wait for basic k8s to come up'''

    TIMEOUT = 2000  # Give k8s 2000s to come up
    RETRY_INTERVAL = 10
    elapsed_time = 0
    prev_cnt = 0
    base_pods = 7

    print('(%02d/%d -- %03ds --) Kubernetes - Wait for basic '
          'Kubernetes infrastructure'
          % (PROGRESS, K8S_FINAL_PROGRESS, (time.time() - start_time)))

    while True:
        pod_status = run_shell(args,
                               'kubectl get pods -n kube-system --no-headers')

        nlines = len(pod_status.splitlines())
        if nlines >= base_pods:
            print(
                '  *All pods %s/%s are started, continuing*' %
                (nlines, base_pods))
            run_shell(args, 'kubectl get pods -n kube-system')
            break
        elif elapsed_time < TIMEOUT:
            if nlines < 0:
                cnt = 0
            else:
                cnt = nlines

            if elapsed_time is not 0:
                if cnt is not prev_cnt:
                    print(
                        "  *Running/Pending pod status after %ds %s/%s*"
                        % (elapsed_time, cnt, base_pods))
            prev_cnt = cnt
            time.sleep(RETRY_INTERVAL)
            elapsed_time = elapsed_time + RETRY_INTERVAL
            continue
        else:
            # Dump verbose output in case it helps...
            print(pod_status)
            raise AbortScriptException(
                "Kubernetes - did not come up after {0} seconds!"
                .format(elapsed_time))
    add_one_to_progress()


def k8s_wait_for_pod_start(args, chart):
    '''Wait for a chart to start'''

    # Useful for debugging issues when Service fails to start
    return

    time.sleep(3)

    while True:
        chart_up = run_shell(args,
                             'kubectl get pods --no-headers --all-namespaces'
                             ' | grep -i "%s" | wc -l' % chart)
        if int(chart_up) == 0:
            print('  *Kubernetes - chart "%s" not started yet*' % chart)
            time.sleep(3)
            continue
        else:
            print('  *Kubernetes - chart "%s" is started*' % chart)
            break


def k8s_wait_for_running_negate(args, timeout=None):
    '''Query get pods until only state is Running'''

    if timeout is None:
        TIMEOUT = 500
    else:
        TIMEOUT = timeout

    RETRY_INTERVAL = 10

    print('  Wait for all pods to be in Running state:')

    elapsed_time = 0
    prev_not_running = 0
    while True:
        etcd_check = run_shell(
            args,
            'kubectl get pods --no-headers --all-namespaces'
            ' | grep -i "request timed out" | wc -l')

        if int(etcd_check) != 0:
            print('Kubernetes - etcdserver is busy - '
                  'retrying after brief pause')
            time.sleep(15)
            continue

        not_running = run_shell(
            args,
            'kubectl get pods --no-headers --all-namespaces | '
            'grep -v "Running" | wc -l')

        if int(not_running) != 0:
            if prev_not_running != not_running:
                print("    *%02d pod(s) are not in Running state*"
                      % int(not_running))
                time.sleep(RETRY_INTERVAL)
                elapsed_time = elapsed_time + RETRY_INTERVAL
                prev_not_running = not_running
            continue
        else:
            print('    *All pods are in Running state*')
            time.sleep(1)
            break

        if elapsed_time > TIMEOUT:
            # Dump verbose output in case it helps...
            print(int(not_running))
            raise AbortScriptException(
                "Kubernetes did not come up after {0} seconds!"
                .format(elapsed_time))
        sys.exit(1)


def add_one_to_progress():
    '''Add one to progress meter'''

    global PROGRESS
    PROGRESS += 1


def clean_progress():
    '''Reset progress meter to zero'''

    global PROGRESS
    PROGRESS = 0


def print_progress(process, msg, finalctr, add_one=False):
    '''Print a message with a progress account'''

    if add_one:
        add_one_to_progress()

    print("(%02d/%02d -- %03ds --) %s - %s" %
          (PROGRESS, finalctr, (time.time() - start_time), process, msg))

    add_one_to_progress()


def k8s_install_tools(args):
    '''Install basic tools needed for first pass'''

    add_one_to_progress()

    print_progress('Kubernetes',
                   'Installing packages',
                   K8S_FINAL_PROGRESS)

    if linux_ver(args) == 'centos':
        run_shell(args, 'sudo yum update -y')
        run_shell(args,
                  'sudo yum install -y qemu epel-release bridge-utils '
                  'python-pip python-devel libffi-devel gcc '
                  'openssl-devel sshpass crudini jq ansible curl lvm2')
    elif linux_ver(args) == 'centos':
        run_shell(args, 'sudo apt-get update; sudo apt-get dist-upgrade -y '
                  '--allow-downgrades --no-install-recommends')
        run_shell(args,
                  'sudo apt-get install --no-install-recommends -y '
                  'qemu bridge-utils python-dev libffi-dev gcc '
                  'libssl-dev python-pip sshpass apt-transport-https git '
                  'gcc crudini jq ansible curl lvm2 ceph-common '
                  'ca-certificates make jq nmap curl uuid-runtime ipcalc '
                  'ebtables ethtool iproute2 iptables libmnl0 '
                  'libnfnetlink0 libwrap0 libxtables11 socat')

        run_shell(args, 'sudo apt autoremove -y && sudo apt autoclean')

    if linux_ver(args) == 'container':
        # Container Linux
        # Very experimental - do all the work here for now
        whoami = run_shell(args, 'whoami')
        if not re.search('root', whoami):
            print('Error - Container Linux must be run as root (sudo su)')
            sys.exit(1)

        run_shell(args, 'systemctl enable docker && systemctl start docker')
        CNI_VERSION = "v0.6.0"
        run_shell(args, 'mkdir -p /opt/cni/bin')
        run_shell(args,
                  'curl -L "https://github.com/containernetworking/'
                  'plugins/releases/download/%s/cni-plugins-amd64-'
                  '%s.tgz" | tar -C /opt/cni/bin -xz'
                  % (CNI_VERSION, CNI_VERSION))
        RELEASE = run_shell(
            args, 'curl -sSL https://dl.k8s.io/release/stable.txt')
        run_shell(args, 'mkdir -p /opt/bin')
        run_shell(args, 'pushd /opt/bin')
        run_shell(args, 'PATH=$PATH:/opt/bin')
        run_shell(args,
                  'curl -L --remote-name-all '
                  'https://storage.googleapis.com/'
                  'kubernetes-release/release/%s/bin/linux/amd64/'
                  '{kubeadm,kubelet,kubectl}' % RELEASE)
        run_shell(args, 'mv kube* /opt/bin')
        run_shell(args, 'chmod +x /opt/bin/kube*')
        run_shell(args,
                  'curl -sSL "https://raw.githubusercontent.com/kubernetes/'
                  'kubernetes/%s/build/debs/kubelet.service" | '
                  'sed "s:/usr/bin:/opt/bin:g" > '
                  '/etc/systemd/system/kubelet.service' % RELEASE)
        run_shell(args,
                  'mkdir -p /etc/systemd/system/kubelet.service.d')
        run_shell(args,
                  'curl -sSL "https://raw.githubusercontent.com/kubernetes/'
                  'kubernetes/%s/build/debs/10-kubeadm.conf" | '
                  'sed "s:/usr/bin:/opt/bin:g" > '
                  '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf'
                  % RELEASE)
        run_shell(args,
                  'systemctl enable kubelet && systemctl start kubelet')
        return

    if '18' in docker_ver(args) and 'ce' in docker_ver(args):
        install_docker = False
    else:
        install_docker = True

    if install_docker:
        if linux_ver(args) == 'centos':
            # https://kubernetes.io/docs/setup/cri/

            run_shell(args,
                      'sudo yum remove -y docker docker-common docker-selinux '
                      'docker-engine')
            run_shell(args,
                      'sudo yum install -y yum-utils '
                      'device-mapper-persistent-data lvm2')
            run_shell(args,
                      'sudo yum-config-manager --add-repo '
                      'https://download.docker.com/linux/centos/'
                      'docker-ce.repo')
            run_shell(args,
                      # 'sudo yum install docker-ce-18.06.1.ce -y')
                      'sudo yum install docker-ce -y')
        else:
            # ubuntu
            # https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-
            # using-the-repository
            run_shell(args,
                      'sudo apt-get -y install '
                      'apt-transport-https '
                      'ca-certificates '
                      'curl '
                      'software-properties-common')
            run_shell(args,
                      'curl -fsSL '
                      'https://download.docker.com/linux/ubuntu/gpg '
                      '| sudo apt-key add -')
            run_shell(args,
                      'sudo add-apt-repository '
                      '"deb [arch=amd64] https://download.docker.com/linux'
                      '/ubuntu '
                      '$(lsb_release -cs) '
                      'stable"')
            run_shell(args, 'sudo apt-get -y update')
            run_shell(args, 'sudo apt-get -y install docker-ce')

        name = '/tmp/daemon'
        with open(name, "w") as w:
            w.write("""\
 {
   "exec-opts": ["native.cgroupdriver=systemd"],
   "log-driver": "json-file",
   "log-opts": {
     "max-size": "100m"
   },
   "storage-driver": "overlay2",
   "storage-opts": [
     "overlay2.override_kernel_check=true"
   ]
}
""")

        run_shell(args, 'sudo chmod 777 %s' % name)
        run_shell(args, 'sudo mv %s /etc/docker/daemon.json' % name)
        run_shell(args, 'sudo mkdir -p /etc/systemd/system/docker.service.d')
        run_shell(args, 'sudo systemctl daemon-reload')
        run_shell(args, 'sudo systemctl enable docker.service')
        run_shell(args, 'sudo systemctl start docker.service')

    if args.destroy is not True:
        print_versions(args)


def k8s_setup_ntp(args):
    '''Setup NTP'''

    if linux_ver(args) == 'container':
        return

    print_progress('Kubernetes',
                   'Setup NTP',
                   K8S_FINAL_PROGRESS)

    if linux_ver(args) == 'centos':
        run_shell(args, 'sudo yum install -y ntp')
        run_shell(args, 'sudo systemctl enable ntpd.service')
        run_shell(args, 'sudo systemctl start ntpd.service')
    else:
        run_shell(args, 'sudo apt-get install -y ntp')
        run_shell(args, 'sudo systemctl restart ntp')


def k8s_turn_things_off(args):
    '''Currently turn off SELinux and Firewall'''

    if linux_ver(args) == 'container':
        return

    run_shell(args, 'sudo swapoff -a')
    run_shell(args, 'sudo modprobe br_netfilter')

    if linux_ver(args) == 'centos':
        print_progress('Kubernetes',
                       'Turn off SELinux',
                       K8S_FINAL_PROGRESS)

        run_shell(args, 'sudo setenforce 0')
        run_shell(args,
                  "sudo sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' "
                  "/etc/selinux/config")
        run_shell(args,
                  "sudo sed -i --follow-symlinks "
                  "'s/SELINUX=enforcing/SELINUX=disabled/g' "
                  "/etc/sysconfig/selinux")

    print_progress('Kubernetes',
                   'Turn off firewall and ISCSID',
                   K8S_FINAL_PROGRESS)

    if linux_ver(args) == 'centos':
        run_shell(args, 'sudo systemctl stop firewalld')
        run_shell(args, 'sudo systemctl disable firewalld')
    else:
        run_shell(args, 'sudo ufw disable')
        run_shell(args, 'sudo systemctl stop iscsid')
        run_shell(args, 'sudo systemctl stop iscsid.service')


def k8s_install_k8s(args):
    '''Necessary repo to install kubernetes and tools'''

    if linux_ver(args) == 'container':
        return

    print_progress('Kubernetes',
                   'Create Kubernetes repo and install Kubernetes ',
                   K8S_FINAL_PROGRESS)

    k8s_create_repo(args)

    if linux_ver(args) == 'centos':
        run_shell(args,
                  'sudo yum install -y kubelet kubeadm kubectl '
                  '--disableexcludes=kubernetes')
    else:
        run_shell(args,
                  'sudo apt-get install -y --allow-downgrades '
                  'ebtables kubelet kubeadm kubectl')


def k8s_setup_dns(args):
    '''DNS services and kubectl fixups'''

    print_progress('Kubernetes',
                   'Setup the DNS server with the service CIDR',
                   K8S_FINAL_PROGRESS)

    run_shell(args,
              'sudo cp /etc/systemd/system/kubelet.service.d/10-kubeadm.conf '
              '/tmp')
    run_shell(args, 'sudo chmod 777 /tmp/10-kubeadm.conf')
    run_shell(args,
              'sudo sed -i s/10.96.0.10/10.3.3.10/g /tmp/10-kubeadm.conf')

    # https://github.com/kubernetes/kubernetes/issues/53333#issuecomment-339793601
    # https://stackoverflow.com/questions/46726216/kubelet-fails-to-get-cgroup-stats-for-docker-and-kubelet-services
    run_shell(
        args,
        'sudo echo Environment="KUBELET_CGROUP_ARGS=--cgroup-driver=systemd" '
        '>> /tmp/10-kubeadm.conf')
    run_shell(
        args,
        'sudo echo Environment="KUBELET_EXTRA_ARGS=--fail-swap-on=false" '
        '>> /tmp/10-kubeadm.conf')
    run_shell(
        args,
        'sudo echo Environment="KUBELET_DOS_ARGS=--runtime-cgroups=/systemd'
        '/system.slice --kubelet-cgroups=/systemd/system.slice --hostname-'
        'override=$(hostname) --fail-swap-on=false" >> /tmp/10-kubeadm.conf')

    run_shell(args, 'sudo mv /tmp/10-kubeadm.conf '
              '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf')


def k8s_reload_service_files(args):
    '''Service files were modified so bring them up again'''

    if linux_ver(args) == 'container':
        return

    print_progress('Kubernetes',
                   'Reload the hand-modified service files',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo systemctl daemon-reload')
    run_shell(args, 'sudo systemctl restart kubelet')


def k8s_start_kubelet(args):
    '''Start kubelet'''

    if linux_ver(args) == 'container':
        return

    print_progress('Kubernetes',
                   'Enable and start kubelet',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo systemctl enable kubelet')
    run_shell(args, 'sudo systemctl start kubelet')


def k8s_fix_iptables(args):
    '''Maybe Centos only but this needs to be changed to proceed'''

    if linux_ver(args) == 'container':
        return

    reload_sysctl = False
    print_progress('Kubernetes',
                   'Fix iptables to enable bridging',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo cp /etc/sysctl.conf /tmp')
    run_shell(args, 'sudo chmod 777 /tmp/sysctl.conf')

    with open('/tmp/sysctl.conf', 'r+') as myfile:
        contents = myfile.read()
        if not re.search('net.bridge.bridge-nf-call-ip6tables=1', contents):
            myfile.write('net.bridge.bridge-nf-call-ip6tables=1' + '\n')
            reload_sysctl = True
        if not re.search('net.bridge.bridge-nf-call-iptables=1', contents):
            myfile.write('net.bridge.bridge-nf-call-iptables=1' + '\n')
            reload_sysctl = True
    if reload_sysctl is True:
        run_shell(args, 'sudo mv /tmp/sysctl.conf /etc/sysctl.conf')
        # run_shell(args, 'sudo sysctl -p')
        run_shell(args, 'sudo sysctl --system')


def k8s_deploy_k8s(args):
    '''Start the kubernetes master'''

    if linux_ver(args) == 'container':
        cmd = '/opt/bin/kubeadm init'
    else:
        cmd = 'sudo kubeadm init --ignore-preflight-errors=all'

    print_progress('Kubernetes',
                   'Deploying using kubeadm (can take a few minutes...)',
                   K8S_FINAL_PROGRESS)

    # out = run_shell(args,  # todo clean up
    #                 'sudo kubeadm init --pod-network-cidr=10.1.0.0/16 '
    #                 '--service-cidr=10.3.3.0/24 '
    #                 '--ignore-preflight-errors=all')
    out = run_shell(args, cmd)

    # Even in no-verbose mode, we need to display the join command to
    # enabled multi-node
    for line in out.splitlines():
        if re.search('kubeadm join', line):
            global JOIN_CMD
            JOIN_CMD = line + ' --ignore-preflight-errors=all'


def k8s_load_kubeadm_creds(args):
    '''This ensures the user gets output from 'kubectl get pods'''

    print_progress('Kubernetes',
                   'Load kubeadm credentials into the system',
                   K8S_FINAL_PROGRESS)

    home = os.environ['HOME']
    kube = os.path.join(home, '.kube')
    config = os.path.join(kube, 'config')

    if not os.path.exists(kube):
        os.makedirs(kube)
    run_shell(args, 'sudo -H cp /etc/kubernetes/admin.conf %s' % config)
    run_shell(args, 'sudo chmod 777 %s' % kube)
    run_shell(args, 'sudo -H chown $(id -u):$(id -g) $HOME/.kube/config')


def k8s_deploy_weave(args):
    '''Deploy CNI/SDN to K8s cluster'''

    print_progress('Kubernetes',
                   'Deploy pod network SDN using Weave CNI',
                   K8S_FINAL_PROGRESS)

    weave_ver = run_shell(args,
                          "echo $(kubectl version | base64 | tr -d '\n')")
    run_shell(args, 'sudo rm -rf /tmp/weave.yaml /tmp/ipalloc.txt')

    curl(
        '-L',
        'https://cloud.weave.works/k8s/net?k8s-version=%s' % weave_ver,
        '-o', '/tmp/weave.yaml')

    # Don't allow Weave Net to crunch ip's used by k8s
    name = '/tmp/ipalloc.txt'
    with open(name, "w") as w:
        w.write("""\
                - name: IPALLOC_RANGE
                  value: 10.0.0.0/16
""")
    run_shell(args, 'chmod 777 /tmp/ipalloc.txt /tmp/weave.yaml')
    run_shell(args, "sed -i '/fieldPath: spec.nodeName/ r "
              "/tmp/ipalloc.txt' /tmp/weave.yaml")

    run_shell(
        args,
        'kubectl apply -f /tmp/weave.yaml')
    return


def k8s_add_api_server(args):
    '''Add API Server'''

    print_progress('Kubernetes',
                   'Add API Server',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo mkdir -p /etc/nodepool/')
    run_shell(args, 'sudo echo %s > /tmp/primary_node_private' % args.mgmt_ip)
    run_shell(args, 'sudo mv -f /tmp/primary_node_private /etc/nodepool')


def k8s_schedule_master_node(args):
    '''Make node an AIO

    Normally master node won't be happy - unless you do this step to
    make it an AOI deployment

    While the command says "taint" the "-" at the end is an "untaint"
    '''

    print_progress('Kubernetes',
                   'Mark master node as schedulable by untainting the node',
                   K8S_FINAL_PROGRESS)

    run_shell(args,
              'kubectl taint nodes '
              '--all=true node-role.kubernetes.io/master:NoSchedule-')


def k8s_update_rbac(args):
    '''Override the default RBAC settings'''

    print_progress('Kubernetes',
                   'Overide default RBAC settings',
                   K8S_FINAL_PROGRESS)
    name = '/tmp/rbac'
    with open(name, "w") as w:
        w.write("""\
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
""")
    run_shell(args, 'kubectl apply -f /tmp/rbac')


def k8s_install_deploy_helm(args):
    '''Deploy helm binary'''

    print_progress('Kubernetes',
                   'Deploy Helm Tiller pod',
                   K8S_FINAL_PROGRESS)

    curl('-sSL',
         'https://storage.googleapis.com/kubernetes-helm/'
         'helm-v%s-linux-amd64.tar.gz' % args.helm_version,
         '-o',
         '/tmp/helm-v%s-linux-amd64.tar.gz' % args.helm_version)
    untar('/tmp/helm-v%s-linux-amd64.tar.gz' % args.helm_version)
    if linux_ver(args) == 'container':
        run_shell(args, 'sudo mv -f linux-amd64/helm /opt/bin')
    else:
        run_shell(args, 'sudo mv -f linux-amd64/helm /usr/local/bin/helm')

    run_shell(args, 'helm init')
    # k8s_wait_for_pod_start(args, 'tiller')
    k8s_wait_for_running_negate(args)


def k8s_final_messages(args):
    '''Final messages and checks'''

    # Store join command for future use
    global JOIN_CMD
    output_file_name = 'join_cmd.txt'
    with open('join_cmd.txt', 'w') as join:
        join.write('sudo %s\n' % JOIN_CMD.lstrip())

    k8s_verify_and_show(args)

    banner("Kuberntes Join")
    print('You can now join any number of Nodes by running the following on '
          'each node as root:')
    print('1. Set up Node as a minion: "k8s.py -m"')
    print('2. "sudo %s"' % JOIN_CMD.lstrip())
    print('3. Join command is also saved here: "%s"' % output_file_name)
    print()

    banner('Kubernetes Cluster ready for use')


def is_running(args, process):
    '''Check if a process is running'''

    s = run_shell(args, 'ps awx')
    for x in s:
        if re.search(process, x):
            return True
        else:
            return False


def k8s_destroy(args):
    '''Destroy and clean up running k8s'''

    if args.destroy is not True:
        return

    clean_progress()
    banner('Kubernetes - Destroying an existing Kubernetes Cluster')

    print_progress('Kubernetes',
                   'Kubeadm reset',
                   K8S_DESTROY_PROGRESS,
                   True)

    run_shell(args, 'sudo kubeadm reset -f')

    print_progress('Kubernetes',
                   'Delete /etc files and dirs',
                   K8S_DESTROY_PROGRESS)

    run_shell(args, 'sudo rm -rf /etc/kubernetes')

    print_progress('Kubernetes',
                   'Delete /var files and dirs',
                   K8S_DESTROY_PROGRESS)

    run_shell(args, 'sudo rm -rf /var/etcd')
    run_shell(args, 'sudo rm -rf /var/run/kubernetes/*')
    run_shell(args, 'sudo rm -rf /var/lib/kubelet/*')
    run_shell(args, 'sudo rm -rf /var/run/lock/kubelet.lock')
    run_shell(args, 'sudo rm -rf /var/run/lock/api-server.lock')
    run_shell(args, 'sudo rm -rf /var/run/lock/etcd.lock')
    run_shell(args, 'sudo rm -rf /var/run/lock/kubelet.lock')

    print_progress('Kubernetes',
                   'Delete /tmp',
                   K8S_DESTROY_PROGRESS)

    run_shell(args, 'sudo rm -rf /tmp/*')

    if os.path.exists('/data'):
        print_progress('Kubernetes',
                       'Remove cinder volumes and data',
                       K8S_DESTROY_PROGRESS)

        run_shell(args, 'sudo vgremove cinder-volumes -f')
        run_shell(args, 'sudo losetup -d /dev/loop0')
        run_shell(args, 'sudo rm -rf /data')

    print_progress('Kubernetes',
                   'Destroy docker containers and images',
                   K8S_DESTROY_PROGRESS)

    # Clean up docker containers
    run_shell(args,
              "sudo docker rm $(sudo docker ps -q -f 'status=exited')")
    run_shell(args,
              "sudo docker rmi $(sudo docker images -q -f "
              "'dangling=true')")
    run_shell(args,
              "sudo docker volume rm -f $(sudo docker volume "
              "ls -qf dangling=true)")

    # Remove docker images on system
    run_shell(args,
              "sudo docker rmi -f $(sudo docker images -a -q)")

    run_shell(args,
              "sudo docker container stop "
              "$(sudo docker container ls -a -q) "
              "&& sudo docker system prune -a -f")

    print_progress('Kubernetes',
                   'Destroy done. Highly recommend rebooting '
                   'your host',
                   K8S_DESTROY_PROGRESS)

    clean_progress()
    add_one_to_progress()

    # After reboot, kubelet service comes back...
    run_shell(args, 'sudo kubeadm reset -f')
    sys.exit(1)


def k8s_check_nslookup(args):
    '''Create a test pod and query nslookup against kubernetes

    Only seems to work in the default namespace

    Also handles the option to create a test pod manually like
    the deployment guide advises.
    '''

    print_progress('Kubernetes',
                   "Bring up test DNS pod",
                   K8S_FINAL_PROGRESS)

    name = './busybox.yaml'
    with open(name, "w") as w:
        w.write("""
apiVersion: v1
kind: Pod
metadata:
  name: k8s-dns-test
spec:
  containers:
  - name: busybox
    image: busybox
    args:
    - sleep
    - "1000000"
""")

    run_shell(args, 'kubectl create -f %s' % name)
    k8s_wait_for_running_negate(args)

    print_progress('Kubernetes',
                   "Test 'nslookup kubernetes'",
                   K8S_FINAL_PROGRESS)

    out = run_shell(args,
                    'kubectl exec k8s-dns-test -- nslookup '
                    'kubernetes | grep -i address | wc -l')
    if int(out) != 2:
        print("  Warning 'nslookup kubernetes ' failed. YMMV continuing")


def k8s_verify_and_show(args):
    '''Run some commands for demo purposes'''

    banner('Kubernetes Verify and Show Deployment')

    print(args, 'Determine IP and port information from Service:')
    print(run_shell(args, 'kubectl get svc -n kube-system'))
    print()

    print(args, 'View all k8s namespaces:')
    print(run_shell(args, 'kubectl get namespaces'))
    print()

    print(args, 'View all deployed services:')
    print(run_shell(args, 'kubectl get deployment -n kube-system'))
    print()

    print(args, 'View configuration maps:')
    print(run_shell(args, 'kubectl get configmap -n kube-system'))
    print()

    print(args, 'General Cluster information:')
    print(run_shell(args, 'kubectl cluster-info'))
    print()

    print(args, 'View all jobs:')
    print(run_shell(args, 'kubectl get jobs --all-namespaces'))
    print()

    print(args, 'View all deployments:')
    print(run_shell(args, 'kubectl get deployments --all-namespaces'))
    print()

    print(args, 'View secrets:')
    print(run_shell(args, 'kubectl get secrets'))
    print()

    print(args, 'View docker images')
    print(run_shell(args, 'sudo docker images'))
    print()

    print(args, 'View deployed Helm Charts')
    print(run_shell(args, 'helm list'))
    print()

    print(args, 'View final cluster:')
    print(run_shell(args, 'kubectl get pods --all-namespaces'))


def k8s_bringup_kubernetes_cluster(args):
    '''Bring up a working Kubernetes Cluster'''

    k8s_destroy(args)
    if args.minion:
        banner('Kubernetes Minion - Install and start needed packages and '
               'services')
    else:
        banner('Kubernetes - Bring up a Cluster')
    k8s_install_tools(args)
    k8s_setup_ntp(args)
    k8s_turn_things_off(args)
    k8s_install_k8s(args)
    if args.minion:
        print_progress('Kubernetes',
                       'start kubelet and docker services',
                       K8S_FINAL_PROGRESS)
        run_shell(args, 'sudo systemctl enable kubelet.service')
        run_shell(args, 'sudo systemctl enable docker.service')
        run_shell(args, 'sudo systemctl start docker.service')
        banner('Kubernetes Minion ready for JOIN command')
        sys.exit(1)
    k8s_reload_service_files(args)
    k8s_start_kubelet(args)
    k8s_fix_iptables(args)
    k8s_deploy_k8s(args)
    k8s_load_kubeadm_creds(args)
    k8s_wait_for_kube_system(args)
    k8s_deploy_weave(args)
    k8s_wait_for_running_negate(args)
    k8s_schedule_master_node(args)


def main():
    '''Main function.'''

    args = parse_args()

    # Force sudo early on
    run_shell(args, 'sudo -v')

    global K8S_DESTROY_PROGRESS
    K8S_DESTROY_PROGRESS = 6

    # Ubuntu does not need the selinux step
    global K8S_FINAL_PROGRESS
    if linux_ver(args) == 'centos':
        K8S_FINAL_PROGRESS = 14
    else:
        K8S_FINAL_PROGRESS = 13

    if args.minion:
        K8S_FINAL_PROGRESS = 5

    set_logging()
    logger.setLevel(level=args.verbose)

    try:
        k8s_destroy(args)
        k8s_bringup_kubernetes_cluster(args)
        k8s_update_rbac(args)
        k8s_install_deploy_helm(args)
        # k8s_install_logging(args)
        k8s_final_messages(args)

    except Exception:
        print('Exception caught:')
        print(sys.exc_info())
        raise


if __name__ == '__main__':
    main()
