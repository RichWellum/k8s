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
import re
import tarfile

__author__ = 'Rich Wellum'
__copyright__ = 'Copyright 2017, Rich Wellum'
__license__ = ''
__version__ = '1.0.0'
__maintainer__ = 'Rich Wellum'
__email__ = 'rwellum@gmail.com'

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
    parser.add_argument('-hv', '--helm_version', type=str, default='2.2.3',
                        help='Specify a different helm version to the default(2.2.3')
    parser.add_argument('-c', '--cleanup', action='store_true',
                        help='Cleanup existing Kubernetes cluster before creating a new one')
    parser.add_argument('-k8s', '--kubernetes', action='store_true',
                        help='Stop after bringing up kubernetes.')
    # parser.add_argument('-l,', '--cloud', type=int, default=3,
    #                     help='optionally change cloud network config files from default(3)')
    parser.add_argument('-v', '--verbose', action='store_const',
                        const=logging.DEBUG, default=logging.INFO,
                        help='turn on verbose messages')

    return parser.parse_args()


def run(cmd, hide_error=False, cont_on_error=True):
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


def untar(fname):
    if (fname.endswith("tar.gz")):
        tar = tarfile.open(fname, "r:gz")
        tar.extractall()
        tar.close()
    elif (fname.endswith("tar")):
        tar = tarfile.open(fname, "r:")
        tar.extractall()
        tar.close()


def start_process(args):
    '''
    Start vboxheadless process
    '''
    logger.debug('args: %s', args)
    with open(os.devnull, 'w') as fp:
        subprocess.Popen((args), stdout=fp)
    time.sleep(2)


def pause_to_debug(str):
    """Pause the script for manual debugging of the VM before continuing."""
    print('Pause: "%s"' % str)
    raw_input('Press Enter to continue')


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


def k8s_wait_for_kube_system():
    """Wait for basic k8s to come up"""

    TIMEOUT = 350  # Give k8s 350s to come up
    RETRY_INTERVAL = 10
    elapsed_time = 0
    print('\nKubernetes - Wait for basic Kubernetes (6 pods) infrastructure')
    while True:
        pod_status = run(['kubectl', 'get', 'pods', '-n', 'kube-system'])
        nlines = len(pod_status.splitlines())
        if nlines - 1 == 6:
            print('Kubernetes - All pods %s/6 are started, continuing' % (nlines - 1))
            p = subprocess.Popen('kubectl get pods -n kube-system',
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
                print('Kubernetes - Pod status after %d seconds, pods up %s:6 - '
                      'sleep %d seconds and retry'
                      % (elapsed_time, cnt, RETRY_INTERVAL))
            time.sleep(RETRY_INTERVAL)
            elapsed_time = elapsed_time + RETRY_INTERVAL
            continue
        else:
            # Dump verbose output in case it helps...
            print(pod_status)
            raise AbortScriptException(
                "Kubernetes - did not come up after {0} seconds!"
                .format(elapsed_time))


def k8s_wait_for_running(number, namespace):
    """Wait for k8s pods to be in running status

    number is the minimum number of 'Running' pods expected"""

    TIMEOUT = 1000  # Give k8s 1000s to come up
    RETRY_INTERVAL = 10

    print("Kubernetes - Wait for %s '%s' pods to be in Running state:"
          % (number, namespace))
    elapsed_time = 0
    while True:
        p = subprocess.Popen('kubectl get pods -n %s | grep "Running" | wc -l' % namespace,
                             stdout=subprocess.PIPE, shell=True)
        (running, err) = p.communicate()
        p.wait()

        if int(running) >= number:
            print('Kubernetes - All Running pods %s:%s' % (int(running), number))
            p = subprocess.Popen('kubectl get pods -n %s' % namespace,
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


def k8s_wait_for_running_negate():
    """Query get pods until only state is Running"""

    TIMEOUT = 1000  # Give k8s 1000s to come up
    RETRY_INTERVAL = 3

    print("Kubernetes - Wait for only running pods to be seen:")
    elapsed_time = 0
    while True:
        p = subprocess.Popen('kubectl get pods --no-headers --all-namespaces | grep -v "Running" | wc -l',
                             stdout=subprocess.PIPE, shell=True)
        (not_running, err) = p.communicate()
        p.wait()

        if int(not_running) != 0:
            print('Kubernetes - Waitng for %s pods to be in Running state' % int(not_running))
            # p = subprocess.Popen('kubectl get pods --all-namespaces',
            #                      stdout=subprocess.PIPE, shell=True)
            # (output, err) = p.communicate()
            # print('%s' % output)
            time.sleep(RETRY_INTERVAL)
            elapsed_time = elapsed_time + RETRY_INTERVAL
            continue
        else:
            print('All pods Running')
            break
        if elapsed_time > TIMEOUT:
            # Dump verbose output in case it helps...
            print(int(not_running))
            raise AbortScriptException(
                "Kubernetes did not come up after {0} 1econds!"
                .format(elapsed_time))
            sys.exit(1)


# def k8s_check_dns():
#     kubectl run - i - t $(uuidgen) - -image = busybox - -restart = Never
#     p = subprocess.Popen('kubectl get pods --all-namespaces',
#                                  stdout=subprocess.PIPE, shell=True)
#             (output, err) = p.communicate()
#             print('%s' % output)


def k8s_turn_things_off():
    print('Kubernetes - Turn off SELinux')
    run(['sudo', 'setenforce', '0'])
    run(['sudo', 'sed', '-i', 's/enforcing/permissive/g', '/etc/selinux/config'])

    print('Kubernetes - Turn off Firewalld if running')
    PROCNAME = 'firewalld'
    for proc in psutil.process_iter():
        if PROCNAME in proc.name():
            print('Found %s, Stopping and Disabling firewalld' % proc.name())
            run(['sudo', 'systemctl', 'stop', 'firewalld'])
            run(['sudo', 'systemctl', 'disable', 'firewalld'])


def k8s_create_repo():
    print('Kubernetes - Creating kubernetes repo')
    create_k8s_repo()
    print('Kubernetes - Installing k8s 1.6.1 or later - please wait')
    subprocess.check_output(
        'sudo yum install -y docker ebtables kubeadm kubectl kubelet kubernetes-cni git gcc', shell=True)


def k8s_setup_dns():
    print('Kubernetes - Start docker and setup the DNS server with the service CIDR')
    run(['sudo', 'systemctl', 'enable', 'docker'])
    run(['sudo', 'systemctl', 'start', 'docker'])
    run(['sudo', 'cp', '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf', '/tmp'])
    run(['sudo', 'chmod', '777', '/tmp/10-kubeadm.conf'])
    run(['sudo', 'sed', '-i', 's/10.96.0.10/10.3.3.10/g', '/tmp/10-kubeadm.conf'])
    run(['sudo', 'mv', '/tmp/10-kubeadm.conf',
         '/etc/systemd/system/kubelet.service.d/10-kubeadm.conf'])


def k8s_reload_service_files():
    print('Kubernetes - Reload the hand-modified service files')
    run(['sudo', 'systemctl', 'daemon-reload'])


def k8s_start_kubelet():
    print('Kubernetes - Enable and start kubelet')
    run(['sudo', 'systemctl', 'enable', 'kubelet'])
    run(['sudo', 'systemctl', 'start', 'kubelet'])


def k8_fix_iptables():
    reload_sysctl = False
    print('Kubernetes - Fix iptables')
    run(['sudo', 'cp', '/etc/sysctl.conf', '/tmp'])
    run(['sudo', 'chmod', '777', '/tmp/sysctl.conf'])

    with open('/tmp/sysctl.conf', 'r+') as myfile:
        contents = myfile.read()
        if not re.search('net.bridge.bridge-nf-call-ip6tables=1', contents):
            myfile.write('net.bridge.bridge-nf-call-ip6tables=1' + '\n')
            reload_sysctl = True
        if not re.search('net.bridge.bridge-nf-call-iptables=1', contents):
            myfile.write('net.bridge.bridge-nf-call-iptables=1' + '\n')
            reload_sysctl = True
    if reload_sysctl is True:
        run(['sudo', 'mv', '/tmp/sysctl.conf', '/etc/sysctl.conf'])
        run(['sudo', 'sysctl', '-p'])


def k8s_deploy_k8s():
    print('Kubernetes - Deploying Kubernetes with kubeadm')
    run(['sudo', 'kubeadm', 'init', '--pod-network-cidr=10.1.0.0/16',
         '--service-cidr=10.3.3.0/24', '--skip-preflight-checks'])


def k8s_load_kubeadm_creds():
    print('Kubernetes - Load kubeadm credentials into the system')
    home = os.environ['HOME']
    kube = os.path.join(home, '.kube')
    config = os.path.join(kube, 'config')

    if not os.path.exists(kube):
        os.makedirs(kube)
    run(['sudo', '-H', 'cp', '/etc/kubernetes/admin.conf', config])
    run(['sudo', 'chmod', '777', kube])
    subprocess.call('sudo -H chown $(id -u):$(id -g) $HOME/.kube/config',
                    shell=True)


def k8s_deploy_canal_sdn():
    print('Kubernetes - Deploy the Canal CNI driver')
    curl(
        '-L',
        'https://raw.githubusercontent.com/projectcalico/canal/master/k8s-install/1.6/rbac.yaml',
        '-o', '/tmp/rbac.yaml')
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


def k8s_schedule_master_node():
    print('Kolla - Mark master node as schedulable')
    run(['kubectl', 'taint', 'nodes', '--all=true',
         'node-role.kubernetes.io/master:NoSchedule-'])


def kolla_update_rbac():
    """..."""
    print('Kolla - Overide default RBAC settings')
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


def kolla_install_deploy_helm(version):
    '''Deploy helm binary'''

    print('Kolla - Install and deploy Helm version %s - Tiller pod' % version)
    url = 'https://storage.googleapis.com/kubernetes-helm/helm-v%s-linux-amd64.tar.gz' % version
    curl('-sSL', url, '-o', '/tmp/helm-v%s-linux-amd64.tar.gz' % version)
    untar('/tmp/helm-v%s-linux-amd64.tar.gz' % version)
    run(['sudo', 'mv', '-f', 'linux-amd64/helm', '/usr/local/bin/helm'])
    run(['helm', 'init'])
    k8s_wait_for_running_negate()
    # k8s_wait_for_running(8, 'kube-system')
    # Check for helm version
    # Todo - replace this to using json path to check for that field
    time.sleep(3)
    out = subprocess.check_output(
        'helm version | grep "%s" | wc -l' % version, shell=True)
    if int(out) == 2:
        print('Kolla - Helm successfully installed')
    else:
        print('Kolla - Warning Helm versions did not match %s' % int(out))


def k8s_cleanup(doit):
    if doit is True:
        print('Cleaning up existing Kubernetes Cluster. YMMV.')
        run(['sudo', 'kubeadm', 'reset'])


def kolla_install_repos():
    print('Kolla - Install repos needed for kolla packaging')
    run(['sudo', 'yum', 'install', '-y', 'epel-release', 'ansible', 'python-pip', 'python-devel'])

    print('Kolla - Clone or update kolla-ansible')
    if os.path.exists('./kolla-ansible'):
        run(['sudo', 'rm', '-rf', './kolla-ansible'])
    run(['git', 'clone', 'http://github.com/openstack/kolla-ansible'])

    print('Kolla - Clone or update kolla-kubernetes')
    if os.path.exists('./kolla-kubernetes'):
        run(['sudo', 'rm', '-rf', './kolla-kubernetes'])
    run(['git', 'clone', 'http://github.com/openstack/kolla-kubernetes'])

    print('Kolla - Install kolla-ansible and kolla-kubernetes')
    run(['sudo', 'pip', 'install', '-U', 'kolla-ansible/', 'kolla-kubernetes/'])

    print('Kolla - Copy default Kolla configuration to /etc')
    run(['sudo', 'cp', '-aR', '/usr/share/kolla-ansible/etc_examples/kolla', '/etc'])

    print('Kolla - Copy default kolla-kubernetes configuration to /etc')
    run(['sudo', 'cp', '-aR', 'kolla-kubernetes/etc/kolla-kubernetes', '/etc'])


def kolla_gen_passwords():
    print('Kolla - Generate default passwords via SPRNG')
    run(['sudo', 'kolla-kubernetes-genpwd'])


def kolla_create_namespace():
    print('Kolla - Create a Kubernetes namespace to isolate this Kolla deployment')
    run(['kubectl', 'create', 'namespace', 'kolla'])


def k8s_label_nodes(node_list):
    print('Kubernetes - Label the AIO nodes')
    for node in node_list:
        subprocess.call('kubectl label node $(hostname) %s=true' % node, shell=True)


def k8s_check_exit(k8s_only):
    if k8s_only is True:
        print('Kubernetes Cluster is running and healthy and you do not wish to install kolla')
        sys.exit(1)


def kolla_modify_globals(MGMT_INT, NEUTRON_INT):
    print('Kolla - Modify globals')

    # Not pythonic but nothing seems to beat sed for quick word replacement
    run(['sudo', 'sed', '-i', 's/#network_interface: "eth0"/network_interface: "%s"/g' % MGMT_INT,
         '/etc/kolla/globals.yml'])
    run(['sudo', 'sed', '-i',
         's/#neutron_external_interface: "eth1"/neutron_external_interface: "%s"/g' % NEUTRON_INT,
         '/etc/kolla/globals.yml'])


def kolla_add_to_globals():
    print('Kolla - Add to globals')

    new = '/tmp/add'
    add_to = '/etc/kolla/globals.yml'

    with open(new, "w") as w:
        w.write("""\
 kolla_install_type: "source"
 tempest_image_alt_id: "{{ tempest_image_id }}"
 tempest_flavor_ref_alt_id: "{{ tempest_flavor_ref_id }}"

 neutron_plugin_agent: "openvswitch"
 api_interface_address: 0.0.0.0
 tunnel_interface_address: 0.0.0.0
 orchestration_engine: KUBERNETES
 memcached_servers: "memcached"
 keystone_admin_url: "http://keystone-admin:35357/v3"
 keystone_internal_url: "http://keystone-internal:5000/v3"
 keystone_public_url: "http://keystone-public:5000/v3"
 glance_registry_host: "glance-registry"
 neutron_host: "neutron"
 keystone_database_address: "mariadb"
 glance_database_address: "mariadb"
 nova_database_address: "mariadb"
 nova_api_database_address: "mariadb"
 neutron_database_address: "mariadb"
 cinder_database_address: "mariadb"
 ironic_database_address: "mariadb"
 placement_database_address: "mariadb"
 rabbitmq_servers: "rabbitmq"
 openstack_logging_debug: "True"
 enable_haproxy: "no"
 enable_heat: "no"
 enable_cinder: "yes"
 enable_cinder_backend_lvm: "yes"
 enable_cinder_backend_iscsi: "yes"
 enable_cinder_backend_rbd: "no"
 enable_ceph: "no"
 enable_elasticsearch: "no"
 enable_kibana: "no"
 glance_backend_ceph: "no"
 cinder_backend_ceph: "no"
 nova_backend_ceph: "no"
""")
    subprocess.call('cat %s | sudo tee -a %s' % (new, add_to), shell=True)


def kolla_enable_qemu():
    print('Kolla - Enable qemu')
    run(['sudo', 'mkdir', '-p', '/etc/kolla/config'])

    new = '/tmp/add'
    add_to = '/etc/kolla/config/nova.conf'
    with open(new, "w") as w:
        w.write("""\
[libvirt]
virt_type = qemu
cpu_mode = none
""")
    run(['sudo', 'mv', new, add_to])


def kolla_gen_configs():
    print('Kolla - Generate the default configuration')
    # Standard jinja2 in Centos7(2.9.6) is broken
    # run(['sudo', 'pip', 'install', 'Jinja2==2.8.1'])
    subprocess.Popen('cd kolla-kubernetes; sudo ansible-playbook -e ' +
                     'ansible_python_interpreter=/usr/bin/python -e ' +
                     '@/etc/kolla/globals.yml -e @/etc/kolla/passwords.yml ' +
                     ' -e CONFIG_DIR=/etc/kolla ansible/site.yml; cd ..',
                     stdout=subprocess.PIPE, shell=True)


def kolla_gen_secrets():
    print('Kolla - Generate the Kubernetes secrets and register them with Kubernetes')
    pause_to_debug('before gen secrets')
    subprocess.Popen('python ./kolla-kubernetes/tools/secret-generator.py create',
                     stdout=subprocess.PIPE, shell=True)

# todo - change Popens to .call and retest

    # mariadb keystone horizon rabbitmq memcached nova-api nova-conductor \
    # nova-scheduler glance-api-haproxy glance-registry-haproxy glance-api \
    # glance-registry neutron-server neutron-dhcp-agent neutron-l3-agent \
    # neutron-metadata-agent neutron-openvswitch-agent openvswitch-db-server \
    # openvswitch-vswitchd nova-libvirt nova-compute nova-consoleauth \
    # nova-novncproxy nova-novncproxy-haproxy neutron-server-haproxy \
    # nova-api-haproxy cinder-api cinder-api-haproxy cinder-backup \
    # cinder-scheduler cinder-volume iscsid tgtd keepalived \
    # placement-api placement-api-haproxy',


def kolla_create_config_maps():
    print('Kolla - Create and register the Kolla config maps')
    pause_to_debug('before creating config maps')
    subprocess.call('kollakube res create configmap \
    mariadb keystone horizon rabbitmq memcached nova-api nova-conductor \
    nova-scheduler glance-api-haproxy glance-registry-haproxy glance-api \
    glance-registry neutron-server neutron-dhcp-agent neutron-l3-agent \
    neutron-metadata-agent neutron-openvswitch-agent openvswitch-db-server \
    openvswitch-vswitchd nova-libvirt nova-compute nova-consoleauth \
    nova-novncproxy nova-novncproxy-haproxy neutron-server-haproxy \
    nova-api-haproxy cinder-api cinder-api-haproxy cinder-backup \
    cinder-scheduler cinder-volume keepalived nova-compute-ironic\
    ironic-api ironic-api-haproxy ironic-conductor ironic-dnsmasq \
    ironic-inspector ironic-inspector-haproxy ironic-pxe \
    placement-api placement-api-haproxy',
                    stdout=subprocess.PIPE, shell=True)
    pause_to_debug('After create config maps')


def kolla_resolve_workaround():
    print('Kolla - Enable resolv.conf workaround')
    run(['./kolla-kubernetes/tools/setup-resolv-conf.sh', 'kolla'])


def kolla_build_micro_charts():
    print('Kolla - Build all Helm microcharts, service charts, and metacharts')
    run(['kolla-kubernetes/tools/helm_build_all.sh', '.'])


def kolla_verify_helm_images():
    out = subprocess.check_output(
        'ls | grep ".tgz" | wc -l', shell=True)
    if int(out) > 150:
        print('Kolla - %s Helm images created' % out)
    else:
        print('Kolla - Error: only %s Helm images created' % out)
        sys.exit(1)


def kolla_create_and_run_cloud(MGMT_INT, MGMT_IP, NEUTRON_INT):
    print('Kolla - Create and run cloud')
    cloud = '/tmp/cloud.yaml'
    with open(cloud, "w") as w:
        w.write("""\
global:
   kolla:
     all:
       image_tag: "4.0.0"
       kube_logger: false
       external_vip: "192.168.7.105"
       base_distro: "centos"
       install_type: "source"
       tunnel_interface: "docker0"
       resolve_conf_net_host_workaround: true
     keystone:
       all:
         admin_port_external: "true"
         dns_name: "192.168.7.105"
       public:
         all:
           port_external: "true"
     rabbitmq:
       all:
         cookie: 67
     glance:
       api:
         all:
           port_external: "true"
     cinder:
       api:
         all:
           port_external: "true"
       volume_lvm:
         all:
           element_name: cinder-volume
         daemonset:
           lvm_backends:
           - '192.168.7.105': 'cinder-volumes'
     ironic:
       conductor:
         daemonset:
           selector_key: "kolla_conductor"
     nova:
       placement_api:
         all:
           port_external: true
       novncproxy:
         all:
           port: 6080
           port_external: true
     openvwswitch:
       all:
         add_port: true
         ext_bridge_name: br-ex
         ext_interface_name: enp1s0f1
         setup_bridge: true
     horizon:
       all:
         port_external: true
""")
    debug = run(['sudo', 'sed', '-i', 's/192.168.7.105/%s/g' % MGMT_IP, cloud])
    pause_to_debug(debug)
    run(['sudo', 'sed', '-i', 's/enp1s0f1/%s/g' % NEUTRON_INT, cloud])
    run(['sudo', 'sed', '-i', 's/docker0/%s/g' % MGMT_INT, cloud])
    pause_to_debug('after sed on cloud')


def helm_install_chart(chart_list, running):
    for chart in chart_list:
        print('Kolla - Install chart: %s' % chart)
        # run(['helm', 'install', '--debug', 'kolla-kubernetes/helm/service/%s' % chart,
        #      '--namespace', 'kolla', '--name', '%s' % chart, '--values', '/tmp/cloud.yaml'])

        p = subprocess.Popen('helm install --debug kolla-kubernetes/helm/service/%s --namespace kolla --name %s --values /tmp/cloud.yaml' % (chart, chart),
                             stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        p.wait()
        print(output)

    k8s_wait_for_running_negate()
    # k8s_wait_for_running(running, 'kolla')


def main():
    """Main function."""
    args = parse_args()

    print('Kubernetes - Management Int:%s, Management IP:%s, Neutron Int:%s' %
          (args.MGMT_INT, args.MGMT_IP, args.NEUTRON_INT))
    print('Helm version %s' % args.helm_version)

    set_logging()
    logger.setLevel(level=args.verbose)

    k8s_cleanup(args.cleanup)

    try:
        # Bring up Kubernetes
        k8s_turn_things_off()
        k8s_create_repo()
        k8s_setup_dns()
        k8s_reload_service_files()
        k8s_start_kubelet()
        k8_fix_iptables()
        k8s_deploy_k8s()
        k8s_load_kubeadm_creds()
        k8s_wait_for_kube_system()
        # k8s_wait_for_running_negate()
        # k8s_wait_for_running(5, 'kube-system')
        k8s_deploy_canal_sdn()
        k8s_wait_for_running_negate()
        # k8s_wait_for_running(7, 'kube-system')
        k8s_schedule_master_node()
        # todo: nslookup check
        k8s_check_exit(args.kubernetes)

        # Start Kolla deployment
        kolla_update_rbac()
        kolla_install_deploy_helm(args.helm_version)
        kolla_install_repos()
        kolla_gen_passwords()
        kolla_create_namespace()

        # Label AOI as Compute and Controller nodes
        node_list = ['kolla_compute', 'kolla_controller']
        k8s_label_nodes(node_list)

        kolla_modify_globals(args.MGMT_INT, args.NEUTRON_INT)
        kolla_add_to_globals()
        kolla_enable_qemu()
        kolla_gen_configs()
        kolla_gen_secrets()
        kolla_create_config_maps()
        kolla_resolve_workaround()
        kolla_build_micro_charts()
        kolla_verify_helm_images()
        kolla_create_and_run_cloud(args.MGMT_INT, args.MGMT_IP, args.NEUTRON_INT)

        # Install Helm charts
        chart_list = ['mariadb']
        helm_install_chart(chart_list, 2)

        # Install remaining service level charts
        chart_list = ['rabbitmq', 'memcached', 'keystone', 'glance', 'cinder-control',
                      'horizon', 'openvswitch', 'neutron', 'nova-control', 'nova-compute']
        helm_install_chart(chart_list, 40)

    except Exception:
        print('Exception caught:')
        print(sys.exc_info())
        raise


if __name__ == '__main__':
    main()
