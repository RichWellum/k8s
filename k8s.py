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

psutil (sudo yum install gcc python-devel
        sudo pip install psutil)
docker (sudopip install docker)
'''

from __future__ import print_function
import sys
import os
import time
import subprocess
# import getpass
import argparse
from argparse import RawDescriptionHelpFormatter
import docker
import re
import logging
import psutil
# import pexpect
# import tarfile


__author__ = "Rich Wellum"
__copyright__ = "Copyright 2017, Rich Wellum"
__license__ = ""
__version__ = "1.0.0"
__maintainer__ = "Rich Wellum"
__email__ = "rwellum@gmail.com"


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
        description="A tool to create a working Kubernetes Cluster \n" +
        "on Bare Metal or a VM.",
        epilog="E.g.: k8s.py eth0 10.192.16.32 eth1\n")
    parser.add_argument('MGMT_INT',
                        help='Management Interface, E.g: eth0')
    parser.add_argument('MGMT_IP',
                        help='Management Interface IP Address, E.g: 10.240.83.111')
    parser.add_argument('NEUTRON_INT',
                        help='Neutron Interface, E.g: eth1')
    # parser.add_argument('-c', '--compute', action='store_true',
    #                     help='optionally will build a compute node')
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


def create_k8s_repo():
    """Create a k8s repository file"""
    # working_dir = '.'
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


def main():
    """Main function."""
    args = parse_args()

    print(args.MGMT_INT, args.MGMT_IP, args.NEUTRON_INT)

    set_logging()
    logger.setLevel(level=args.verbose)

    try:
        print("Turn off SELinux")
        run(['sudo', 'setenforce', '0'])
        run(['sudo', 'sed', '-i', 's/enforcing/permissive/g', '/etc/selinux/config'])

        print("Turn off Firewalld if running")
        PROCNAME = "firewalld"
        for proc in psutil.process_iter():
            if PROCNAME in proc.name():
                print("Found %s, Stopping and Disabling firewalld" % proc.name())
                run(['sudo', 'systemctl', 'stop', 'firewalld'])
                run(['sudo', 'systemctl', 'disable', 'firewalld'])

        print("Installing k8s 1.6.1 or later - please wait")
        create_k8s_repo()
        run(['sudo', 'yum', 'install', '-y', 'docker', 'ebtables',
             'kubeadm', 'kubectl', 'kubelet', 'kubernetes-cni', 'git', 'gcc'])

        print("Enable the correct cgroup driver and disable CRI")
        run(['sudo', 'systemctl', 'enable', 'docker'])
        run(['sudo', 'systemctl', 'start', 'docker'])
        CGROUP_DRIVER = subprocess.check_output(
            'sudo docker info | grep "Cgroup Driver" | awk "{print $3}"')
        print(CGROUP_DRIVER)
        # client = docker.from_env()
        # for x in client.info():
        #     print (x)
        # print(client.info())
        # DOCKER_INFO = run(['sudo', 'docker', 'info', '|', 'grep', 'Cgroup Driver'])
        # DOCKER_INFO = subprocess.check_output(
        #     'sudo docker info | grep Cgroup Driver')
        # print(DOCKER_INFO)
        # num = 1
        # for line in DOCKER_INFO:
        #     num = num + 1
        #     if re.search(line, 'Cgroup Driver'):
        #         print(line)
        #     print('LINE %s %s' % (num, line))
        # fields = line.strip().split()
        # Array indices start at 0 unlike AWK
        # print(fields[0])
        # , | grep "Cgroup Driver"

    except Exception:
        print("Exception caught:")
        print(sys.exc_info())
        raise


if __name__ == '__main__':
    main()
