    Building your own OpenStack Image (keystone) from private source and running it
    with kolla-kubernetes OpenStack:
    ===============================================================================
    Building kolla images with custom repos - many ops want to do it and do not want
    upstream/out-of-the-box repos that kolla provides, and want kolla to build
    internal/curated custom packages.


    This example uses keystone...


    Pull in your own source
    =======================
    Know where you put your source as you'll need this to build the image...

    E.g. git clone git@10.240.205.131:thinkcloud/keystone.git

    $ ls -ah ~/keystone/
    .                 .coveragerc  .gitignore   LICENSE      releasenotes      test-requirements.txt
    ..                doc          .gitreview   .mailmap     requirements.txt  tests-py3-blacklist.txt
    babel.cfg         etc          HACKING.rst  MANIFEST.in  setup.cfg         tools
    config-generator  examples     httpd        rally-jobs   setup.py          tox.ini
    CONTRIBUTING.rst  .git         keystone     README.rst   .testr.conf

    Get kolla repo
    ==============
    git clone http://github.com/openstack/kolla


    Compile kolla
    =============
    sudo -H pip install -U kolla


    Generate kolla-build.conf
    =========================
    sudo pip install tox
    cd kolla; tox -e genconfig


    Optional - Edit kolla-build.conf and add in source
    ==================================================
    vi etc/kolla/kolla-build.conf

        install_type = source


    Edit kolla-build.conf and add pointer to source
    ===============================================
    $ vi etc/kolla/kolla-build.conf
    [keystone-base]
    type = local
    location = ~/keystone/
    reference = stable/mitaka

    (Note this is fine for a single OpenStack Service - but replacing all services?

    For keystone, Cinder and Horizon:
    git clone git@10.240.205.131:thinkcloud/horizon.git
    git clone git@10.240.205.131:thinkcloud/cinder.git

    [horizon]
    type = local
    location = ~/horizon/
    reference = stable/mitaka

    [cinder-base]
    type = local
    location = ~/cinder/
    reference = stable/mitaka


    Build kolla keystone images
    ===========================
    Use source keyword (drop 'keystone' if you want to build everything)

    sudo kolla-build -t source keystone

    Or push to a registry:

    kolla-build --registry 172.22.2.81:5000 --push -t source keystone

    *Where the ip address is the ip of the server you run docker registry container

    For all three images:

    sudo kolla-build -t source horizon cinder keystone


    Check for valid generated image
    ===============================
    docker images | grep keystone (look at timestamp)

    rwellum@ubuntuk8s:~/openstack$ sudo docker images | grep keystone
    kolla/centos-source-keystone-ssh                         5.0.0               83ec593bba18        14 hours ago        1.136 GB
    kolla/centos-source-keystone-fernet                      5.0.0               cb838ed0d927        14 hours ago        1.116 GB
    kolla/centos-source-keystone                             5.0.0               67fa7d97d066        14 hours ago        1.092 GB
    kolla/centos-source-keystone-base                        5.0.0               c80b6ce870dc        14 hours ago        1.092 GB
    kolla/centos-source-barbican-keystone-listener           5.0.0               3e626a8c07e3        14 hours ago        1.047 GB

    rwellum@ubuntuk8s:~$ sudo docker images | grep horizon | grep 5.0.0
    kolla/centos-source-horizon                              5.0.0               5182810deebb        2 minutes ago       1.077 GB
    rwellum@ubuntuk8s:~$ sudo docker images | grep cinder | grep 5.0.0
    kolla/centos-source-cinder-volume                        5.0.0               69a838d5fcf9        4 minutes ago       1.166 GB
    kolla/centos-source-cinder-backup                        5.0.0               2a5c157df76d        4 minutes ago       1.166 GB
    kolla/centos-source-cinder-api                           5.0.0               dc011787c2cc        4 minutes ago       1.213 GB
    kolla/centos-source-cinder-scheduler                     5.0.0               64c92f8cb61e        5 minutes ago       1.137 GB
    kolla/centos-source-cinder-base                          5.0.0               613e0c645bf9        5 minutes ago       1.137 GB


    Add image generated to cloud.yml
    ================================
    Add to your cloud.yml the image_full tage and point to docker image location:

    KEYSTONE:
        keystone:
           all:
    +         image_full: kolla/centos-source-keystone:5.0.0
             admin_port_external: "true"
             dns_name: "10.240.43.250"
             port: 5000

    If running multinode replace the local location with the docker registry address

    Note that cell support was added to 4.0.0 - so mitaka (3.0.0) will break.

    Set: global.kolla.nova.all.cell_enabled=false
        nova:
           all:
    +         cell_enabled: false
    +

    Same with placement api:

    global.kolla.nova.all.placement_api_enabled

    (Remove placement_id?)

         nova:
    +       all:
    +         cell_enabled: false
    +         placement_api_enabled: false

    HORIZON:
         horizon:
           all:
    +         image_full: kolla/centos-source-horizon:5.0.0

    CINDER:

        cinder:
    +       all:
    +         image_full: kolla/centos-source-cinder-base:5.0.0

    ===

    Running OpenStack
    =================
    Select the tag that matches the version of OpenStack you've replaced (mitaka=3.0.0) and select --edit-config
    rwellum@ubuntuk8s:~/openstack$ ../k8s/ko.py ens3 10.240.43.250 ens4 10.240.43.55 -it 3.0.3 -ec
