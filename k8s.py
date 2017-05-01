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
'''

from __future__ import print_function
import sys
import os
import time
import subprocess
import getpass
import argparse
from argparse import RawDescriptionHelpFormatter
import re
import logging
import pexpect
import tarfile


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
        "Bare Metal or a VM.",
        epilog="E.g.:\n" +
        "Build CIMP XML files(and QCOW2's): k8s.py eth0 10.192.16.32 eth1\n")
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


def main():
    """Main function."""
    args = parse_args()

    set_logging()
    logger.setLevel(level=args.verbose)

    # Generate ifcfg files
    logger.debug('Cloud %s' % args.cloud)
    cimp_cfg_files = tarfile.open("%s/cimp_cfg_files.tar.gz" % working_dir, 'w:gz')
    create_cfg_files(cimp_cfg_files, args.cloud)
    cimp_cfg_files.close()

    # Generate README
    create_readme()

    # Entered xclarity qcow2 and roller ISO are placed in /var/running
    # on the server
    var_images_running = '/var/images/running'

    cmd_str = 'mkdir -p %s' % var_images_running
    subprocess.check_output(cmd_str, shell=True)

    var_images_controller = '/var/images/controller'
    cmd_str = 'mkdir -p %s' % var_images_controller
    subprocess.check_output(cmd_str, shell=True)

    # Create tar files
    cimp_node1 = tarfile.open("%s/cimp_node1.tar.gz" % working_dir, 'w:gz')
    cimp_node2 = tarfile.open("%s/cimp_node2.tar.gz" % working_dir, 'w:gz')
    cimp_node3 = tarfile.open("%s/cimp_node3.tar.gz" % working_dir, 'w:gz')
    if args.compute:
        cimp_node4 = tarfile.open("%s/cimp_node4.tar.gz" % working_dir, 'w:gz')

    # Grab xclarity qcow2 image and copy to images
    if not os.path.exists(args.XCLARITY_QCOW2):
        logger.error('Did not find %s' % args.XCLARITY_QCOW2)
        sys.exit(1)
    else:
        logger.debug('Found valid %s' % args.XCLARITY_QCOW2)

    xclarity_qcow2_name_path = os.path.join(
        var_images_running, os.path.basename(args.XCLARITY_QCOW2))
    if os.path.exists(xclarity_qcow2_name_path):
        logger.info('Found %s, will not copy again' % xclarity_qcow2_name_path)
    else:
        cmd_str = 'cp %s %s' % (args.XCLARITY_QCOW2, var_images_running)
        subprocess.check_output(cmd_str, shell=True)
        logger.info('Copied %s to %s' % (args.XCLARITY_QCOW2, xclarity_qcow2_name_path))

    # Grab roller iso image and copy to images
    if not os.path.exists(args.ROLLER_ISO):
        logger.error('Did not find %s' % args.ROLLER_ISO)
        sys.exit(1)
    else:
        logger.debug('Found valid %s' % args.ROLLER_ISO)

    roller_iso_name_path = os.path.join(var_images_running, os.path.basename(args.ROLLER_ISO))
    if os.path.exists(roller_iso_name_path):
        logger.info('Found %s, will not copy again' % roller_iso_name_path)
    else:
        cmd_str = 'cp %s %s' % (args.ROLLER_ISO, var_images_running)
        subprocess.check_output(cmd_str, shell=True)
        logger.info('Copied %s to %s' % (args.ROLLER_ISO, roller_iso_name_path))

    try:
        # Roller
        xml_path, images_path, controller_path = create_dirs(1)
        qcow2_name = 'roller.qcow2'
        qcow2_name_path = os.path.join(images_path, qcow2_name)
        vm_type = 'roller'
        xml_name = '%s%s' % (vm_type,  '.xml')

        cmd_str = 'qemu-img create -f qcow2 %s 600G' % qcow2_name
        subprocess.check_output(cmd_str, shell=True)
        cmd_str = 'sudo mv %s %s' % (qcow2_name, images_path)
        subprocess.check_output(cmd_str, shell=True)
        logger.info('Created %s' % qcow2_name_path)
        add_to_tar(cimp_node1, qcow2_name_path)

        qcow_xml = os.path.join(var_images_running, qcow2_name)
        qcow2_list = [qcow_xml]

        boot = 'destroy'
        controller = ''
        build_common_xml(qcow2_list, xml_path, xml_name, vm_type,
                         roller_port, roller_mem, roller_vcpu, boot,
                         controller, roller_iso_name_path)
        xml_name_path = os.path.join(xml_path, xml_name)
        logger.info('Created %s' % xml_name_path)
        cmd_str = '/usr/bin/virt-xml-validate %s domain' % xml_name_path
        subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
        add_to_tar(cimp_node1, xml_name_path)

        # Controller
        boot = 'restart'

        for i in range(1, 4):
            # Build all 3 controllers
            xml_path, images_path, controller_path = create_dirs(i)

            qcow2_name_os = 'controller%s_os%s' % (i, '.qcow2')
            qcow2_name_path_os = os.path.join(controller_path,
                                              qcow2_name_os)
            qcow2_name_mongo = 'controller%s_mongo%s' % (i, '.qcow2')
            qcow2_name_path_mongo = os.path.join(controller_path,
                                                 qcow2_name_mongo)

            vm_type = 'controller'
            xml_name = '%s%s%s' % (vm_type, i, '.xml')

            cmd_str = 'qemu-img create -f qcow2 %s 128G' % qcow2_name_os
            subprocess.check_output(cmd_str, shell=True)
            cmd_str = 'sudo mv %s %s' % (qcow2_name_os, controller_path)
            subprocess.check_output(cmd_str, shell=True)
            logger.info('Created %s' % qcow2_name_path_os)

            cmd_str = 'qemu-img create -f qcow2 %s 80G' % qcow2_name_mongo
            subprocess.check_output(cmd_str, shell=True)
            cmd_str = 'sudo mv %s %s' % (qcow2_name_mongo, controller_path)
            subprocess.check_output(cmd_str, shell=True)
            logger.info('Created %s' % qcow2_name_path_mongo)

            if i == 1:
                p = cimp_node1
            elif i == 2:
                p = cimp_node2
            else:
                p = cimp_node3

            add_to_tar(p, qcow2_name_path_os)
            add_to_tar(p, qcow2_name_path_mongo)

            qcow_xml_os = os.path.join(var_images_controller,
                                       '%s' % qcow2_name_os)
            qcow_xml_mongo = os.path.join(var_images_controller,
                                          '%s' % qcow2_name_mongo)
            qcow2_list = [qcow_xml_os, qcow_xml_mongo]

            build_common_xml(qcow2_list, xml_path, xml_name, vm_type,
                             i, controller_mem, controller_vcpu, boot, i)
            xml_name_path = os.path.join(xml_path, xml_name)
            logger.info('Created %s' % xml_name_path)
            cmd_str = '/usr/bin/virt-xml-validate %s domain' % xml_name_path
            subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
            add_to_tar(p, xml_name_path)

        # Xclarity
        xml_path, images_path, controller_path = create_dirs(1)
        vm_type = 'xclarity'
        xml_name = '%s%s' % (vm_type,  '.xml')
        qcow2_name_path = xclarity_qcow2_name_path
        qcow_xml = os.path.join(var_images_running, qcow2_name_path)
        qcow2_list = [qcow_xml]

        boot = 'restart'

        build_common_xml(qcow2_list, xml_path, xml_name, vm_type,
                         xclarity_port, xclarity_mem, xclarity_vcpu, boot)
        xml_name_path = os.path.join(xml_path, xml_name)
        logger.info('Created %s' % xml_name_path)
        cmd_str = '/usr/bin/virt-xml-validate %s domain' % xml_name_path
        subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
        add_to_tar(cimp_node1, xml_name_path)

        if args.compute:
            # Compute
            xml_path, images_path, controller_path = create_dirs(4)
            qcow2_name = 'compute.qcow2'
            qcow2_name_path = os.path.join(controller_path, qcow2_name)
            vm_type = 'compute'
            xml_name = '%s%s' % (vm_type,  '.xml')

            cmd_str = 'qemu-img create -f qcow2 %s 600G' % qcow2_name
            subprocess.check_output(cmd_str, shell=True)
            cmd_str = 'sudo mv %s %s' % (qcow2_name, controller_path)
            subprocess.check_output(cmd_str, shell=True)
            logger.info('Created %s' % qcow2_name_path)
            add_to_tar(cimp_node4, qcow2_name_path)
            qcow_xml = os.path.join(var_images_running, qcow2_name)
            qcow2_list = [qcow_xml]

            boot = 'restart'

            build_common_xml(qcow2_list, xml_path, xml_name, vm_type,
                             compute_port, compute_mem, compute_vcpu, boot)
            xml_name_path = os.path.join(xml_path, xml_name)
            logger.info('Created %s' % xml_name_path)
            cmd_str = '/usr/bin/virt-xml-validate %s domain' % xml_name_path
            subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
            add_to_tar(cimp_node4,  xml_name_path)

    except Exception:
        print("Exception caught:")
        print(sys.exc_info())
        raise

    cimp_node1.close()
    cimp_node2.close()
    cimp_node3.close()
    if args. compute:
        cimp_node4.close()

    # Clean up
    for path in glob.glob('%s/*' % working_dir):
        if os.path.isdir(path):
            shutil.rmtree(path)
        if 'ifcfg' in path:
            os.remove(path)

    logger.info("Created %s/cimp_node1.tar.gz" % working_dir)
    logger.info("Created %s/cimp_node2.tar.gz" % working_dir)
    logger.info("Created %s/cimp_node3.tar.gz" % working_dir)
    if args.compute:
        logger.info("Created %s/cimp_node4.tar.gz" % working_dir)
    logger.info("Unpack %s/cimp_node1.tar.gz with 'tar xvf' and " % working_dir)
    logger.info(" move ./images/running/* to /var/images/running/*")
    logger.info(" move ./var/images/running/* to /var/images/running/*")
    logger.info(" move ./images/controller/* to /var/images/controller/*")
    logger.info("scp cimp_node2.tar.gz to physical server 'cimp_node2' ")
    logger.info(" Unpack %s/cimp_node2.tar.gz with 'tar xvf' and " % working_dir)
    logger.info(" move ./var/images/running/* to /var/images/running/*")
    logger.info(" move ./images/controller/* to /var/images/controller/*")
    logger.info("scp cimp_node3.tar.gz to physical server 'cimp_node3' ")
    logger.info(" Unpack %s/cimp_node3.tar.gz with 'tar xvf' and " % working_dir)
    logger.info(" move ./var/images/running/* to /var/images/running/*")
    logger.info(" move ./images/controller/* to /var/images/controller/*")

    print('VNC Access Ports - IP Address on br-mgmt:')
    print('Roller: 5900, Controller1: 5901, Controller2: 5902, Controller3: 5903, XClarity: 5904')
    print('E.g. access Roller during bringup: xvnc4viewer 192.168.10.22:5900')


if __name__ == '__main__':
    main()
