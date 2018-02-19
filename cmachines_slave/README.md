Required packages
=================

```
sudo apt-get install expect
```

Install Docker CE

```
https://docs.docker.com/
```

docker pull jinpengli/docker-image-reverse-ssh-tunnel


Install
=======

Configure Docker to use the btrfs storage driver

https://docs.docker.com/engine/userguide/storagedriver/btrfs-driver/#configure-docker-to-use-the-btrfs-storage-driver


```
$ sudo cp -au /var/lib/docker /var/lib/docker.bk
$ sudo rm -rf /var/lib/docker/*
$ sudo mkfs.btrfs -f /dev/xvdf /dev/xvdg
$ sudo mount -t btrfs /dev/xvdf /var/lib/docker
```

btrfs
------

On a fresh BTRFS filesystem, enabling quota is as simple as typing btrfs quota enable <path>
On an existing BTRFS filesystem first enable the quotas and check if btrfs qgroup show <path> returns anything, if not, your BTRFS version does not create qgroups automatically. To create the qgroups, you must:
Enable the quota system. btrfs quota enable <path>
Create the basic qgroups. btrfs subvolume list <path> | cut -d' ' -f2 | xargs -I{} -n1 btrfs qgroup create 0/{} <path>
Rescan the filesystem. btrfs quota rescan <path>


Other
============

the docker service should be started with 

sudo systemctl start nvidia-docker

You CANNOT start it with docker directly!

sudo btrfs quota enable /var/lib/docker
sudo btrfs quota rescan /var/lib/docker

then you can start the chongdata service!!!!

Network Configuration
---------------------

limit the bandwidth (download 256KB and upload 50KB)

sudo wondershaper eno1 2048 400


