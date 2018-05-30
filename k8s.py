#!/usr/bin/env python

'''
k8s.py - Kubernetes deployer

Purpose
=======

Features
========
1. Supports both Centos and Ubuntu natively.

2. Requires just a VM with two NIC's, low congnitive overhead:
'ko.py int1 int2'.

4. Options to change the versions of all the tools, like helm, kubernetes etc.

6. Easy on the eye output, with optional verbose mode for more information.

7. Contains a demo mode that walks the user through each step with additional
information and instruction.

11. Cleans up previous deployment with --cc option

13. Select between Canal and Weave CNI's for inter-pod communications.

14. Optionally installs a fluent-bit container for log aggregation to ELK.

15. Option to create a kubernetes minion to add to existing deployment.

Host machine requirements
=========================

The host machine must satisfy the following minimum requirements:

- 2 network interfaces
- 8GB min, 16GB preferred RAM
- 40G min, 80GB preferred disk space
- 2 CPU's Min, 4 preferred CPU's
- Root access to the deployment host machine

Prerequisites
=============

Verify the state of network interfaces. If using a VM spawned on OpenStack as
the host machine, the state of the second interface will be DOWN on booting
the VM.

    ip addr show

Bring up the second network interface if it is down.

    ip link set ens4 up

However as this interface will be used for Neutron External, this Interface
should not have an IP Address. Verify this with.

    ip addr show


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

To create two interfaces like this in Ubuntu, for example:

Edit /etc/network/interfaces:

# The primary network interface
auto ens3
iface ens3 inet dhcp

# Neutron network interface (up but no ip address)
auto ens4
iface ens4 inet manual
ifconfig ens4 up

TODO
====

1. Convert to using https://github.com/kubernetes-incubator/client-python
2. Note there are various todo's scattered inline as well.

Recomendations
==============
1. Due to the length the script can run for, recomend disabling sudo timeout:

sudo visudo
Add: 'Defaults    timestamp_timeout=-1'

2. Due to the length of time the script can run for, I recommend using nohup

E.g. nohup python -u k8s.py eth0 eth1

Then in another window:

tail -f nohup.out

3. Can be run remotely with:

curl https://raw.githubusercontent.com/RichWellum/k8s/master/ko.py \
| python - ens3 ens4 --image_version master -cni weave
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


logger = logging.getLogger(__name__)

# Nasty globals but used universally
global PROGRESS
PROGRESS = 0

global K8S_FINAL_PROGRESS
K8S_FINAL_PROGRESS = 0


def set_logging():
    '''Set basic logging format.'''

    FORMAT = "[%(asctime)s.%(msecs)03d %(levelname)8s: "\
        "%(funcName)20s:%(lineno)s] %(message)s"
    logging.basicConfig(format=FORMAT, datefmt="%H:%M:%S")


class AbortScriptException(Exception):
    '''Abort the script and clean up before exiting.'''


def parse_args():
    '''Parse sys.argv and return args'''

    parser = argparse.ArgumentParser(  # todo: rewrite
        formatter_class=RawDescriptionHelpFormatter,
        description='This tool provides a method to deploy OpenStack on a '
        'Kubernetes Cluster using Kolla\nand Kolla-Kubernetes on bare metal '
        'servers or virtual machines.\nVirtual machines supported are Ubuntu '
        'and Centos. \nUsage as simple as: "ko.py eth0 eth1"\n'
        'The host machine must satisfy the following minimum requirements:\n'
        '- 2 network interfaces\n'
        '- 8GB min, 16GB preferred - main memory\n'
        '- 40G min, 80GB preferred - disk space\n'
        '- 2 CPUs Min, 4 preferred - CPUs\n'
        'Root access to the deployment host machine is required.',
        epilog='E.g.: ko.py eth0 eth1 -iv master -cni weave --logs\n')
    # parser.add_argument('MGMT_INT',
    #                     help='The interface to which Kolla binds '
    #                     'API services, E.g: eth0')
    # parser.add_argument('NEUTRON_INT',
    #                     help='The interface that will be used for the '
    #                     'external bridge in Neutron, E.g: eth1')
    # parser.add_argument('-mi', '--mgmt_ip', type=str, default='None',
    #                     help='Provide own MGMT ip address Address, '
    #                     'E.g: 10.240.83.111')
    # parser.add_argument('-vi', '--vip_ip', type=str, default='None',
    #                     help='Provide own Keepalived VIP, used with '
    #                     'keepalived, should be an unused IP on management '
    #                     'NIC subnet, E.g: 10.240.83.112')
    # parser.add_argument('-iv', '--image_version', type=str, default='ocata',
    #                     help='Specify a different Kolla image version to '
    #                     'the default (ocata)')
    # parser.add_argument('-it', '--image_tag', type=str,
    #                     help='Specify a different Kolla tag version to '
    #                     'the default which is the same as the image_version '
    #                     'by default')
    parser.add_argument('-hv', '--helm_version', type=str, default='2.8.1',
                        help='Specify a different helm version to the '
                        'default(2.8.1)')
    parser.add_argument('-kv', '--k8s_version', type=str, default='1.10.0',
                        help='Specify a different kubernetes version to '
                        'the default(1.10.0) - note 1.8.0 is the minimum '
                        'supported')
    # parser.add_argument('-av', '--ansible_version', type=str,
    #                     default='2.4.2.0',
    #                     help='Specify a different ansible version to '
    #                     'the default(2.4.2.0)')
    # parser.add_argument('-jv', '--jinja2_version', type=str, default='2.10',
    #                     help='Specify a different jinja2 version to '
    #                     'the default(2.10)')
    # parser.add_argument('-dr', '--docker_repo', type=str, default='kolla',
    #                     help='Specify a different docker repo from '
    #                     'the default(kolla), for example "rwellum" has '
    #                     'the latest pike images')
    parser.add_argument('-cni', '--cni', type=str, default='canal',
                        help='Specify a different CNI/SDN to '
                        'the default(canal), like "weave"')
    parser.add_argument('-l', '--logs', action='store_true',
                        help='Install fluent-bit container')
    # parser.add_argument('-k8s', '--kubernetes', action='store_true',
    #                     help='Stop after bringing up kubernetes, '
    #                     'do not install OpenStack')
    parser.add_argument('-cm', '--create_minion', action='store_true',
                        help='Do not install Kubernetes or OpenStack, '
                        'useful for preparing a multi-node minion')
    parser.add_argument('-v', '--verbose', action='store_const',
                        const=logging.DEBUG, default=logging.INFO,
                        help='Turn on verbose messages')
    parser.add_argument('-d', '--demo', action='store_true',
                        help='Display some demo information and '
                        'offer to move on')
    parser.add_argument('-f', '--force', action='store_true',
                        help='When used in conjunction with --demo - it '
                        'will proceed without user input.')
    parser.add_argument('-c', '--cleanup', action='store_true',
                        help='YMMV: Cleanup existing Kubernetes cluster '
                        'before creating a new one. Because LVM is not '
                        'cleaned up, space will be used up. '
                        '"-cc" is far more reliable but requires a reboot')
    parser.add_argument('-cc', '--complete_cleanup', action='store_true',
                        help='Cleanup existing Kubernetes cluster '
                        'then exit, rebooting host is advised')

    return parser.parse_args()


def run_shell(args, cmd):
    '''Run a shell command and return the output

    Print the output and errors if debug is enabled
    Not using logger.debug as a bit noisy for this info
    '''

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    out, err = p.communicate()

    if args.demo:
        if not re.search('kubectl get pods', cmd):
            print('DEMO: CMD: "%s"' % cmd)

    out = out.rstrip()
    err = err.rstrip()

    if args.verbose == 10:  # Hack - debug enabled
        if str(out) is not '0' and str(out) is not '1' and out:
            print("Shell STDOUT output: \n'%s'\n" % out)
        if err:
            print("Shell STDERR output: \n'%s'\n" % err)

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


def pause_tool_execution(str):
    '''Pause the script for manual debugging of the VM before continuing'''

    print('Pause: "%s"' % str)
    raw_input('Press Enter to continue\n')


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


def demo(args, title, description):
    '''Pause the script to provide demo information'''

    if not args.demo:
        return

    banner = len(description)
    if banner > 100:
        banner = 100

    # First banner
    print('\n')
    for c in range(banner):
        print('*', end='')

    # Add DEMO string
    print('\n%s'.ljust(banner - len('DEMO')) % 'DEMO')

    # Add title formatted to banner length
    print('%s'.ljust(banner - len(title)) % title)

    # Add description
    print('%s' % description)

    # Final banner
    for c in range(banner):
        print('*', end='')
    print('\n')

    if not args.force:
        raw_input('Press Enter to continue with demo...')
    else:
        print('Demo: Continuing with Demo')


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


def linux_ver():
    '''Determine Linux version - Ubuntu or Centos

    Fail if it is not one of those.
    Return the long string for output
    '''

    find_os = platform.linux_distribution()
    if re.search('Centos', find_os[0], re.IGNORECASE):
        linux = 'centos'
    elif re.search('Ubuntu', find_os[0], re.IGNORECASE):
        linux = 'ubuntu'
    else:
        print('Linux "%s" is not supported yet' % find_os[0])
        sys.exit(1)

    return(linux)


def linux_ver_det():
    '''Determine Linux version - Ubuntu or Centos

    Return the long string for output
    '''

    return(str(platform.linux_distribution()))


def docker_ver(args):
    '''Display docker version'''

    oldstr = run_shell(args, "docker --version | awk '{print $3}'")
    newstr = oldstr.replace(",", "")
    return(newstr.rstrip())


def tools_versions(args, str):
    '''A Dictionary of tools and their versions

    Defaults are populated by tested well known versions.

    User can then overide each individual tool.

    Return a Version for a string.
    '''

    tools = [
        "helm",
        "kubernetes"]

    # This should match up with the defaults set in parse_args
    #           helm     k8s
    versions = ["2.8.1", "1.10.0"]

    tools_dict = {}
    # Generate dictionary
    for i in range(len(tools)):
        tools_dict[tools[i]] = versions[i]

    # Now overide based on user input - first
    if tools_dict["helm"] is not args.helm_version:
        tools_dict["helm"] = args.helm_version
    if tools_dict["kubernetes"] is not args.k8s_version:
        tools_dict["kubernetes"] = args.k8s_version

    return(tools_dict[str])


def print_versions(args):
    '''Print out lots of information

    Tool versions, networking, user options and more
    '''

    banner('Kubernetes - Bring up a Kubernetes Cluster')
    print('\nLinux Host Info:    %s' % linux_ver_det())

    print('\nNetworking Info:')
    print('  CNI/SDN:            %s' % args.cni)

    print('\nTool Versions:')
    print('  Docker version:     %s' % docker_ver(args))
    print('  Helm version:       %s' % tools_versions(args, 'helm'))
    print('  K8s version:        %s'
          % tools_versions(args, 'kubernetes').rstrip())

    print('\nOptions:')
    print('  Logging enabled:    %s' % args.logs)
    print('  Dev mode enabled:   %s' % args.dev_mode)
    print('  No Network:         %s' % args.no_network)
    print('  Demo mode:          %s' % args.demo)
    print('  Edit Cloud:         %s' % args.edit_cloud)
    print('  Edit Globals:       %s' % args.edit_globals)
    print('\n')
    time.sleep(2)


def k8s_create_repo(args):
    '''Create a k8s repository file'''

    if linux_ver() == 'centos':
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
        # todo: add -H to all sudo's see if it works in both envs
        run_shell(args, 'sudo mv ./kubernetes.repo %s' % repo)
    else:
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
    base_pods = 6

    print('(%02d/%d) Kubernetes - Wait for basic '
          'Kubernetes (6 pods) infrastructure'
          % (PROGRESS, K8S_FINAL_PROGRESS))

    while True:
        pod_status = run_shell(args,
                               'kubectl get pods -n kube-system --no-headers')
        nlines = len(pod_status.splitlines())
        if nlines == 6:
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
                        "  *Running pod(s) status after %d seconds %s:%s*"
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

    if 'cinder' in chart:
        chart = 'cinder'

    if 'nova' in chart:
        chart = 'nova'

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
        TIMEOUT = 1000
    else:
        TIMEOUT = timeout

    RETRY_INTERVAL = 3

    print('  Wait for all pods to be in Running state:')

    elapsed_time = 0
    prev_not_running = 0
    while True:
        etcd_check = run_shell(args,
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
                "Kubernetes did not come up after {0} 1econds!"
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
    print("(%02d/%02d) %s - %s" % (PROGRESS, finalctr, process, msg))
    add_one_to_progress()


def k8s_install_tools(args):
    '''Basic tools needed for first pass'''

    # Reset kubeadm if it's a new installation
    if not args.openstack:
        run_shell(args, 'sudo kubeadm reset')

    print_progress('Kubernetes',
                   'Installing environment',
                   K8S_FINAL_PROGRESS)

    if linux_ver() == 'centos':
        run_shell(args, 'sudo yum update -y; sudo yum upgrade -y')
        run_shell(args, 'sudo yum install -y qemu epel-release bridge-utils')
        run_shell(args,
                  'sudo yum install -y python-pip python-devel libffi-devel '
                  'gcc openssl-devel sshpass')
        run_shell(args, 'sudo yum install -y git crudini jq ansible curl lvm2')
        # Disable swap as not supported. TODO: check with ubuntu
        run_shell(args, 'sudo swapoff -a')
        run_shell(args, 'sudo yum install -y docker')
    else:
        run_shell(args, 'sudo apt-get update; sudo apt-get dist-upgrade -y '
                  '--allow-downgrades --no-install-recommends')
        run_shell(args, 'sudo apt-get install -y qemu bridge-utils')
        run_shell(args, 'sudo apt-get install -y python-dev libffi-dev gcc '
                  'libssl-dev python-pip sshpass apt-transport-https')
        run_shell(args, 'sudo apt-get install -y git gcc crudini jq '
                  'ansible curl lvm2')
        run_shell(args, 'sudo apt autoremove -y && sudo apt autoclean')
        run_shell(args, 'sudo apt-get install -y docker.io')

    curl(
        '-L',
        'https://bootstrap.pypa.io/get-pip.py',
        '-o', '/tmp/get-pip.py')
    run_shell(args, 'sudo python /tmp/get-pip.py')

    # https://github.com/ansible/ansible/issues/26670
    run_shell(args, 'sudo -H pip uninstall pyOpenSSL -y')
    run_shell(args, 'sudo -H pip install pyOpenSSL')


def k8s_setup_ntp(args):
    '''Setup NTP'''

    print_progress('Kubernetes',
                   'Setup NTP',
                   K8S_FINAL_PROGRESS)

    if linux_ver() == 'centos':
        run_shell(args, 'sudo yum install -y ntp')
        run_shell(args, 'sudo systemctl enable ntpd.service')
        run_shell(args, 'sudo systemctl start ntpd.service')
    else:
        run_shell(args, 'sudo apt-get install -y ntp')
        run_shell(args, 'sudo systemctl restart ntp')


def k8s_turn_things_off(args):
    '''Currently turn off SELinux and Firewall'''

    if linux_ver() == 'centos':
        print_progress('Kubernetes',
                       'Turn off SELinux',
                       K8S_FINAL_PROGRESS)

        run_shell(args, 'sudo setenforce 0')
        run_shell(args,
                  'sudo sed -i s/enforcing/permissive/g /etc/selinux/config')

    print_progress('Kubernetes',
                   'Turn off firewall and ISCSID',
                   K8S_FINAL_PROGRESS)

    if linux_ver() == 'centos':
        run_shell(args, 'sudo systemctl stop firewalld')
        run_shell(args, 'sudo systemctl disable firewalld')
    else:
        run_shell(args, 'sudo ufw disable')
        run_shell(args, 'sudo systemctl stop iscsid')
        run_shell(args, 'sudo systemctl stop iscsid.service')


def k8s_install_k8s(args):
    '''Necessary repo to install kubernetes and tools

    This is often broken and may need to be more programatic
    '''

    print_progress('Kubernetes',
                   'Create Kubernetes repo and install Kubernetes ',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo -H pip install --upgrade pip')
    k8s_create_repo(args)

    demo(args, 'Installing Kubernetes', 'Installing docker ebtables '
         'kubelet-%s kubeadm-%s kubectl-%s kubernetes-cni' %
         (tools_versions(args, 'kubernetes'),
          tools_versions(args, 'kubernetes'),
          tools_versions(args, 'kubernetes')))

    if linux_ver() == 'centos':
        # run_shell(args,
        #           'sudo yum install -y ebtables kubelet-%s '
        #           'kubeadm-%s kubectl-%s kubernetes-cni'
        #           % (tools_versions(args, 'kubernetes'),
        #              tools_versions(args, 'kubernetes'),
        #              tools_versions(args, 'kubernetes')))
        run_shell(args,
                  'sudo yum install -y '
                  'ebtables kubelet kubeadm kubectl kubernetes-cni')

    else:
        # todo - this breaks when ubuntu steps up a revision to -01 etc
        # run_shell(args,
        #           'sudo apt-get install -y --allow-downgrades '
        #           'ebtables kubelet kubeadm kubectl '
        #           'kubernetes-cni' % (tools_versions(args, 'kubernetes'),
        #                               tools_versions(args, 'kubernetes'),
        #                               tools_versions(args, 'kubernetes')))
        run_shell(args,
                  'sudo apt-get install -y --allow-downgrades '
                  'ebtables kubelet kubeadm kubectl kubernetes-cni')


def k8s_setup_dns(args):
    '''DNS services and kubectl fixups'''

    print_progress('Kubernetes',
                   'Start docker and setup the DNS server with '
                   'the service CIDR',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo systemctl enable docker')
    run_shell(args, 'sudo systemctl start docker')
    run_shell(
        args,
        'sudo cp /etc/systemd/system/kubelet.service.d/10-kubeadm.conf /tmp')
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
    '''Service files where modified so bring them up again'''

    print_progress('Kubernetes',
                   'Reload the hand-modified service files',
                   K8S_FINAL_PROGRESS)

    run_shell(args, 'sudo systemctl daemon-reload')


def k8s_start_kubelet(args):
    '''Start kubelet'''

    print_progress('Kubernetes',
                   'Enable and start kubelet',
                   K8S_FINAL_PROGRESS)

    demo(args, 'Enable and start kubelet',
         'kubelet is a command line interface for running commands '
         'against Kubernetes clusters')

    run_shell(args, 'sudo systemctl enable kubelet')
    run_shell(args, 'sudo systemctl start kubelet')


def k8s_fix_iptables(args):
    '''Maybe Centos only but this needs to be changed to proceed'''

    reload_sysctl = False
    print_progress('Kubernetes',
                   'Fix iptables to enable bridging',
                   K8S_FINAL_PROGRESS)

    demo(args, 'Centos fix bridging',
         'Setting net.bridge.bridge-nf-call-iptables=1 '
         'in /etc/sysctl.conf')

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
        run_shell(args, 'sudo sysctl -p')


def k8s_deploy_k8s(args):
    '''Start the kubernetes master'''

    print_progress('Kubernetes',
                   'Deploying Kubernetes with kubeadm (Slow!)',
                   K8S_FINAL_PROGRESS)

    demo(args, 'Initializes your Kubernetes Master',
         'One of the most frequent criticisms of Kubernetes is that it is '
         'hard to install.\n'
         'Kubeadm is a new tool that is part of the Kubernetes distribution '
         'that makes this easier')
    demo(args, 'The Kubernetes Control Plane',
         'The Kubernetes control plane consists of the Kubernetes '
         'API server\n'
         '(kube-apiserver), controller manager (kube-controller-manager),\n'
         'and scheduler (kube-scheduler). The API server depends '
         'on etcd so\nan etcd cluster is also required.\n'
         'https://www.ianlewis.org/en/how-kubeadm-initializes-'
         'your-kubernetes-master')
    demo(args, 'kubeadm and the kubelet',
         'Kubernetes has a component called the Kubelet which '
         'manages containers\nrunning on a single host. It allows us to '
         'use Kubelet to manage the\ncontrol plane components. This is '
         'exactly what kubeadm sets us up to do.\n'
         'We run:\n'
         'kubeadm init --pod-network-cidr=10.1.0.0/16 '
         '--service-cidr=10.3.3.0/24 --ignore-preflight-errors=all '
         'and check output\n'
         'Run: "watch -d sudo docker ps" in another window')
    demo(args, 'Monitoring Kubernetes',
         'What monitors Kubelet and make sure it is always running? This '
         'is where we use systemd.\n Systemd is started as PID 1 so the OS\n'
         'will make sure it is always running, systemd makes sure the '
         'Kubelet is running, and the\nKubelet makes sure our containers '
         'with the control plane components are running.')

    if args.demo:
        print(run_shell(args,
                        'sudo kubeadm init --pod-network-cidr=10.1.0.0/16 '
                        '--service-cidr=10.3.3.0/24 '
                        '--ignore-preflight-errors=all'))
        demo(args, 'What happened?',
             'We can see above that kubeadm created the necessary '
             'certificates for\n'
             'the API, started the control plane components, '
             'and installed the essential addons.\n'
             'The join command is important - it allows other nodes '
             'to be added to the existing resources\n'
             'Kubeadm does not mention anything about the Kubelet but '
             'we can verify that it is running:')
        print(run_shell(args,
                        'sudo ps aux | grep /usr/bin/kubelet | grep -v grep'))
        demo(args,
             'Kubelet was started. But what is it doing? ',
             'The Kubelet will monitor the control plane components '
             'but what monitors Kubelet and make sure\n'
             'it is always running? This is where we use systemd. '
             'Systemd is started as PID 1 so the OS\n'
             'will make sure it is always running, systemd makes '
             'sure the Kubelet is running, and the\nKubelet '
             'makes sure our containers with the control plane '
             'components are running.')
    else:
        out = run_shell(args,
                        'sudo kubeadm init --pod-network-cidr=10.1.0.0/16 '
                        '--service-cidr=10.3.3.0/24 '
                        '--ignore-preflight-errors=all')
        # Even in no-verbose mode, we need to display the join command to
        # enabled multi-node
        for line in out.splitlines():
            if re.search('kubeadm join', line):
                print('  You can now join any number of machines by '
                      'running the following on each node as root:')
                line += ' ' * 2
                print(line)


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
    demo(args, 'Verify Kubelet',
         'Kubelete should be running our control plane components and be\n'
         'connected to the API server (like any other Kubelet node.\n'
         'Run "watch -d kubectl get pods --all-namespaces" in another '
         'window\nNote that the kube-dns-* pod is not ready yet. We do '
         'not have a network yet')
    demo(args, 'Verifying the Control Plane Components',
         'We can see that kubeadm created a /etc/kubernetes/ '
         'directory so check\nout what is there.')
    if args.demo:
        print(run_shell(args, 'ls -lh /etc/kubernetes/'))
        demo(args, 'Files created by kubectl',
             'The admin.conf and kubelet.conf are yaml files that mostly\n'
             'contain certs used for authentication with the API. The pki\n'
             'directory contains the certificate authority certs, '
             'API server\ncerts, and tokens:')
        print(run_shell(args, 'ls -lh /etc/kubernetes/pki'))
        demo(args, 'The manifests directory ',
             'This directory is where things get interesting. In the\n'
             'manifests directory we have a number of json files for our\n'
             'control plane components.')
        print(run_shell(args, 'sudo ls -lh /etc/kubernetes/manifests/'))
        demo(args, 'Pod Manifests',
             'If you noticed earlier the Kubelet was passed the\n'
             '--pod-manifest-path=/etc/kubernetes/manifests flag '
             'which tells\nit to monitor the files in the '
             '/etc/kubernetes/manifests directory\n'
             'and makes sure the components defined therein are '
             'always running.\nWe can see that they are running my '
             'checking with the local Docker\nto list the running containers.')
        print(
            run_shell(args,
                      'sudo docker ps --format="table {{.ID}}\t{{.Image}}"'))
        demo(args, 'Note above containers',
             'We can see that etcd, kube-apiserver, '
             'kube-controller-manager, and\nkube-scheduler are running.')
        demo(args, 'How can we connect to containers?',
             'If we look at each of the json files in the '
             '/etc/kubernetes/manifests\ndirectory we can see that they '
             'each use the hostNetwork: true option\nwhich allows the '
             'applications to bind to ports on the host just as\n'
             'if they were running outside of a container.')
        demo(args, 'Connect to the API',
             'So we can connect to the API servers insecure local port.\n'
             'curl http://127.0.0.1:8080/version')
        print(run_shell(args, 'sudo curl http://127.0.0.1:8080/version'))
        demo(args, 'Secure port?', 'The API server also binds a secure'
             'port 443 which\nrequires a client cert and authentication. '
             'Be careful to use the\npublic IP for your master here.\n'
             'curl --cacert /etc/kubernetes/pki/ca.pem '
             'https://10.240.0.2/version')
        print(run_shell(args, 'curl --cacert /etc/kubernetes/pki/ca.pem '
                        'https://10.240.0.2/version'))
    print('  Note "kubectl get pods --all-namespaces" should work now')


def k8s_deploy_cni(args):
    '''Deploy CNI/SDN to K8s cluster'''

    if args.cni == 'weave':
        print_progress('Kubernetes',
                       'Deploy pod network SDN using Weave CNI',
                       K8S_FINAL_PROGRESS)

        weave_ver = run_shell(args,
                              "echo $(kubectl version | base64 | tr -d '\n')")
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

    # If not weave then canal...
    # The ip range in canal.yaml,
    # /etc/kubernetes/manifests/kube-controller-manager.yaml
    # and the kubeadm init command must match
    print_progress('Kubernetes',
                   'Deploy pod network SDN using Canal CNI',
                   K8S_FINAL_PROGRESS)

    answer = curl(
        '-L',
        'https://raw.githubusercontent.com/projectcalico/canal/master/'
        'k8s-install/1.7/rbac.yaml',
        '-o', '/tmp/rbac.yaml')
    logger.debug(answer)
    run_shell(args, 'kubectl create -f /tmp/rbac.yaml')

    if args.demo:
        demo(args, 'Why use a CNI Driver?',
             'Container Network Interface (CNI) is a '
             'specification started by CoreOS\n'
             'with the input from the wider open '
             'source community aimed to make network\n'
             'plugins interoperable between container '
             'execution engines. It aims to be\n'
             'as common and vendor-neutral as possible '
             'to support a wide variety of\n'
             'networking options from MACVLAN to modern '
             'SDNs such as Weave and flannel.\n\n'
             'CNI is growing in popularity. It got its '
             'start as a network plugin\n'
             'layer for rkt, a container runtime from CoreOS. '
             'CNI is getting even\n'
             'wider adoption with Kubernetes adding support for '
             'it. Kubernetes\n'
             'accelerates development cycles while simplifying '
             'operations, and with\n'
             'support for CNI is taking the next step toward a '
             'common ground for\nnetworking.')
    answer = curl(
        '-L',
        'https://raw.githubusercontent.com/projectcalico/canal/master/'
        'k8s-install/1.7/canal.yaml',
        '-o', '/tmp/canal.yaml')
    logger.debug(answer)
    run_shell(args, 'sudo chmod 777 /tmp/canal.yaml')
    run_shell(args,
              'sudo sed -i s@10.244.0.0/16@10.1.0.0/16@ /tmp/canal.yaml')
    run_shell(args, 'kubectl create -f /tmp/canal.yaml')
    demo(args,
         'Wait for CNI to be deployed',
         'A successfully deployed CNI will result in a valid dns pod')


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

    demo(args,
         'Running on the master is different though',
         'There is a special annotation on our node '
         'telling Kubernetes not to\n'
         'schedule containers on our master node.')
    run_shell(args,
              'kubectl taint nodes '
              '--all=true node-role.kubernetes.io/master:NoSchedule-')


# def kolla_update_rbac(args):
#     '''Override the default RBAC settings'''

#     print_progress('Kolla',
#                    'Overide default RBAC settings',
#                    KOLLA_FINAL_PROGRESS)

#     demo(args, 'Role-based access control (RBAC)',
#          'A method of regulating access to computer or '
#          'network resources based\n'
#          'on the roles of individual users within an enterprise. '
#          'In this context,\n'
#          'access is the ability of an individual user to perform a '
#          'specific task\n'
#          'such as view, create, or modify a file.')
#     name = '/tmp/rbac'
#     with open(name, "w") as w:
#         w.write("""\
# apiVersion: rbac.authorization.k8s.io/v1
# kind: ClusterRoleBinding
# metadata:
#   name: cluster-admin
# roleRef:
#   apiGroup: rbac.authorization.k8s.io
#   kind: ClusterRole
#   name: cluster-admin
# subjects:
# - kind: Group
#   name: system:masters
# - kind: Group
#   name: system:authenticated
# - kind: Group
#   name: system:unauthenticated
# """)
#     if args.demo:
#         print(run_shell(args, 'kubectl apply -f /tmp/rbac'))
#         demo(args, 'Note the cluster-admin has been replaced', '')
#     else:
#         run_shell(args, 'kubectl apply -f /tmp/rbac')


def k8s_install_deploy_helm(args):
    '''Deploy helm binary'''

    print_progress('Kolla',
                   'Deploy Helm Tiller pod',
                   K8S_FINAL_PROGRESS)

    demo(args, 'Download the version of helm requested and install it',
         'Installing means the Tiller Server will be instantiated in a pod')
    curl('-sSL',
         'https://storage.googleapis.com/kubernetes-helm/'
         'helm-v%s-linux-amd64.tar.gz' % args.helm_version,
         '-o',
         '/tmp/helm-v%s-linux-amd64.tar.gz' % args.helm_version)
    untar('/tmp/helm-v%s-linux-amd64.tar.gz' % args.helm_version)
    run_shell(args, 'sudo mv -f linux-amd64/helm /usr/local/bin/helm')
    run_shell(args, 'helm init')
    k8s_wait_for_pod_start(args, 'tiller')
    k8s_wait_for_running_negate(args)
    # Check for helm version
    # Todo - replace this to using json path to check for that field
    while True:
        out = run_shell(args,
                        'helm version | grep "%s" | wc -l' %
                        args.helm_version)
        if int(out) == 2:
            print_progress('Kolla',
                           'Helm successfully installed',
                           K8S_FINAL_PROGRESS)
            break
        else:
            time.sleep(1)
            continue

    demo(args, 'Check running pods..',
         'Note that the helm version in server and client is the same.\n'
         'Tiller is ready to respond to helm chart requests')


def is_running(args, process):
    '''Check if a process is running'''

    s = run_shell(args, 'ps awx')
    for x in s:
        if re.search(process, x):
            return True
        else:
            return False


def k8s_cleanup(args):
    '''Cleanup on Isle 9'''

    if args.cleanup is True or args.complete_cleanup is True:
        clean_progress()
        banner('Kubernetes - Cleaning up an existing Kubernetes Cluster')

        print_progress('Kubernetes',
                       'Kubeadm reset',
                       K8S_CLEANUP_PROGRESS,
                       True)

        run_shell(args, 'sudo kubeadm reset')

        print_progress('Kubernetes',
                       'Delete /etc files and dirs',
                       K8S_CLEANUP_PROGRESS)

        run_shell(args, 'sudo rm -rf /etc/kolla*')
        run_shell(args, 'sudo rm -rf /etc/kubernetes')
        run_shell(args, 'sudo rm -rf /etc/kolla-kubernetes')

        print_progress('Kubernetes',
                       'Delete /var files and dirs',
                       K8S_CLEANUP_PROGRESS)

        run_shell(args, 'sudo rm -rf /var/lib/kolla*')
        run_shell(args, 'sudo rm -rf /var/etcd')
        run_shell(args, 'sudo rm -rf /var/run/kubernetes/*')
        run_shell(args, 'sudo rm -rf /var/lib/kubelet/*')
        run_shell(args, 'sudo rm -rf /var/run/lock/kubelet.lock')
        run_shell(args, 'sudo rm -rf /var/run/lock/api-server.lock')
        run_shell(args, 'sudo rm -rf /var/run/lock/etcd.lock')
        run_shell(args, 'sudo rm -rf /var/run/lock/kubelet.lock')

        print_progress('Kubernetes',
                       'Delete /tmp',
                       K8S_CLEANUP_PROGRESS)

        run_shell(args, 'sudo rm -rf /tmp/*')

        if os.path.exists('/data'):
            print_progress('Kubernetes',
                           'Remove cinder volumes and data',
                           K8S_CLEANUP_PROGRESS)

            run_shell(args, 'sudo vgremove cinder-volumes -f')
            run_shell(args, 'sudo losetup -d /dev/loop0')
            run_shell(args, 'sudo rm -rf /data')

        print_progress('Kubernetes',
                       'Cleanup docker containers and images',
                       K8S_CLEANUP_PROGRESS)

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

        if args.complete_cleanup:
            print_progress('Kubernetes',
                           'Cleanup done. Highly recommend rebooting '
                           'your host',
                           K8S_CLEANUP_PROGRESS)
        else:
            print_progress('Kubernetes',
                           'Cleanup done. Will attempt '
                           'to proceed with installation. YMMV.\n',
                           K8S_CLEANUP_PROGRESS)

            clean_progress()
            add_one_to_progress()

    # After reboot, kubelet service comes back...
    run_shell(args, 'sudo kubeadm reset')


def k8s_check_exit(k8s_only):
    '''If the user only wants kubernetes and not kolla - stop here'''

    if k8s_only is True:
        print('Kubernetes Cluster is running and healthy and you do '
              'not wish to install kolla')
        sys.exit(1)


def k8s_get_pods(args, namespace):
    '''Display all pods per namespace list'''

    for name in namespace:
        final = run_shell(args, 'kubectl get pods -n %s' % name)

        print_progress('Kolla',
                       'Final Kolla Kubernetes OpenStack '
                       'pods for namespace %s:' % name,
                       K8S_FINAL_PROGRESS)

        print(final)


def k8s_check_nslookup(args):
    '''Create a test pod and query nslookup against kubernetes

    Only seems to work in the default namespace

    Also handles the option to create a test pod manually like
    the deployment guide advises.
    '''

    print_progress('Kubernetes',
                   "Test 'nslookup kubernetes' - bring up test pod",
                   K8S_FINAL_PROGRESS)

    demo(args, 'Lets create a simple pod and verify that DNS works',
         'If it does not then this deployment will not work.')
    name = './busybox.yaml'
    with open(name, "w") as w:
        w.write("""
apiVersion: v1
kind: Pod
metadata:
  name: kolla-dns-test
spec:
  containers:
  - name: busybox
    image: busybox
    args:
    - sleep
    - "1000000"
""")
    demo(args, 'The busy box yaml is: %s' % name, '')
    if args.demo:
        print(run_shell(args, 'sudo cat ./busybox.yaml'))

    run_shell(args, 'kubectl create -f %s' % name)
    k8s_wait_for_running_negate(args)
    out = run_shell(args,
                    'kubectl exec kolla-dns-test -- nslookup '
                    'kubernetes | grep -i address | wc -l')
    demo(args, 'Kolla DNS test output: "%s"' % out, '')
    if int(out) != 2:
        print("  Warning 'nslookup kubernetes ' failed. YMMV continuing")
    else:
        banner("Kubernetes Cluster is up and running")


def kubernetes_test_cli(args):
    '''Run some commands for demo purposes'''

    if not args.demo:
        return

    demo(args, 'Test CLI:', 'Determine IP and port information from Service:')
    print(run_shell(args, 'kubectl get svc -n kube-system'))
    print(run_shell(args, 'kubectl get svc -n kolla'))

    demo(args, 'Test CLI:', 'View all k8s namespaces:')
    print(run_shell(args, 'kubectl get namespaces'))

    demo(args, 'Test CLI:', 'Kolla Describe a pod in full detail:')
    print(run_shell(args, 'kubectl describe pod ceph-admin -n kolla'))

    demo(args, 'Test CLI:', 'View all deployed services:')
    print(run_shell(args, 'kubectl get deployment -n kube-system'))

    demo(args, 'Test CLI:', 'View configuration maps:')
    print(run_shell(args, 'kubectl get configmap -n kube-system'))

    demo(args, 'Test CLI:', 'General Cluster information:')
    print(run_shell(args, 'kubectl cluster-info'))

    demo(args, 'Test CLI:', 'View all jobs:')
    print(run_shell(args, 'kubectl get jobs --all-namespaces'))

    demo(args, 'Test CLI:', 'View all deployments:')
    print(run_shell(args, 'kubectl get deployments --all-namespaces'))

    demo(args, 'Test CLI:', 'View secrets:')
    print(run_shell(args, 'kubectl get secrets'))

    demo(args, 'Test CLI:', 'View docker images')
    print(run_shell(args, 'sudo docker images'))

    demo(args, 'Test CLI:', 'View deployed Helm Charts')
    print(run_shell(args, 'helm list'))

    demo(args, 'Test CLI:', 'Working cluster kill a pod and watch resilience.')
    demo(args, 'Test CLI:', 'kubectl delete pods <name> -n kolla')


def k8s_bringup_kubernetes_cluster(args):
    '''Bring up a working Kubernetes Cluster

    Explicitly using the Canal CNI for now
    '''

    if args.openstack:
        print('Kolla - Building OpenStack on existing Kubernetes cluster')
        return

    k8s_cleanup(args)
    k8s_install_tools(args)
    k8s_setup_ntp(args)
    k8s_turn_things_off(args)
    k8s_install_k8s(args)
    if args.create_minion:
        run_shell(args, 'sudo systemctl enable kubelet.service')
        run_shell(args, 'sudo systemctl enable docker.service')
        run_shell(args, 'sudo systemctl start docker.service')
        banner('Kubernetes tools installed, minion ready')
        sys.exit(1)
    k8s_setup_dns(args)
    k8s_reload_service_files(args)
    k8s_start_kubelet(args)
    k8s_fix_iptables(args)
    k8s_deploy_k8s(args)
    k8s_load_kubeadm_creds(args)
    k8s_wait_for_kube_system(args)
    k8s_add_api_server(args)
    k8s_deploy_cni(args)
    k8s_wait_for_pod_start(args, 'canal')
    k8s_wait_for_running_negate(args)
    k8s_schedule_master_node(args)
    k8s_check_nslookup(args)
    k8s_check_exit(args.kubernetes)
    demo(args, 'Congrats - your kubernetes cluster should be up '
         'and running now', '')


def kolla_install_logging(args):
    '''Install log collection

    Experimental to test out various centralized logging options

    https://github.com/kubernetes/charts/blob/master/stable/fluent-bit/values.yaml

    Kafka can be added, but it's only available in a dev image.

    repository: fluent/fluent-bit-kafka-dev
    tag: 0.4

    Note that both changes to the forwarder and kafka require changes to
    the helm chart.
    '''

    if not args.logs:
        return

    name = '/tmp/fluentd_values.yaml'
    with open(name, "w") as w:
        w.write("""\
# Minikube stores its logs in a seperate directory.
# enable if started in minikube.
on_minikube: false

image:
  fluent_bit:
    repository: fluent/fluent-bit
    tag: 0.12.10
  pullPolicy: Always

backend:
  type: forward
  forward:
    host: fluentd
    port: 24284
  es:
    host: elasticsearch
    port: 9200
  kafka:
    # See dev image note above
    host: kafka
    port: 9092
    topics: test
    brokers: kafka:9092

env: []

resources:
  limits:
    memory: 100Mi
  requests:
    cpu: 100m
    memory: 100Mi

# Node tolerations for fluent-bit scheduling to nodes with taints
# Ref: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/
##
tolerations: []
#- key: "key"
#  operator: "Equal|Exists"
#  value: "value"
#  effect: "NoSchedule|PreferNoSchedule|NoExecute(1.6 only)"

# Node labels for fluent-bit pod assignment
# Ref: https://kubernetes.io/docs/user-guide/node-selection/
##
nodeSelector: {}
""")

    print_progress('Kolla',
                   'Install fluent-bit log aggregator',
                   K8S_FINAL_PROGRESS)
    run_shell(args,
              'helm install --name my-release -f %s '
              'stable/fluent-bit' % name)
    k8s_wait_for_running_negate(args)


def main():
    '''Main function.'''

    args = parse_args()

    # Force sudo early on
    run_shell(args, 'sudo -v')

    global K8S_CLEANUP_PROGRESS

    # Ubuntu does not need the selinux step
    global K8S_FINAL_PROGRESS
    if linux_ver() == 'centos':
        K8S_FINAL_PROGRESS = 16
    else:
        K8S_FINAL_PROGRESS = 15

    if args.create_minion:
        K8S_FINAL_PROGRESS = 5

    set_logging()
    logger.setLevel(level=args.verbose)

    if args.complete_cleanup is not True:
        print_versions(args)

    try:
        if args.complete_cleanup:
            k8s_cleanup(args)
            sys.exit(1)

        # k8s_test_vip_int(args)
        k8s_bringup_kubernetes_cluster(args)
        k8s_install_deploy_helm(args)
        kubernetes_test_cli(args)

    except Exception:
        print('Exception caught:')
        print(sys.exc_info())
        raise


if __name__ == '__main__':
    main()
