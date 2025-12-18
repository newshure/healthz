ARG REGISTRY_ADDRESS=registry.docker.address
ARG PROJECT=base_images
ARG CATEGORY=health
ARG IMAGE_NAME=healthz
ARG TAG=latest
ARG APP_USER=healthz

FROM ${REGISTRY_ADDRESS}/${PROJECT_NAME}/${CATEGORY_NAME}/${IMAGE_NAME}:${TAG}


# set user to use root commands
USER root

# install packages for convenience
RUN dnf update -y                                                                         &&\
    dnf install -y bash iputils net-tools telnet procps-ng ncurses openssh-clients sudo     \
    nmap-ncat bind-utils openldap-clients krb5-workstation                                &&\
    dnf clean all
    
# add users and grroups
RUN groupadd -g 777 haedong && useradd -g 777 -u 777 -m -c /bin/bash haedong              &&\
    groupadd -g 1000 APP_USER_GROUP && useradd -g 1000 -u 1000 -m -c /bin/bash $APP_USER  &&\
    echo 'haedong:P@SSw0rd' | chpasswd && echo '$APP_USER:P@SSw0rd' | chpasswd            &&\
    chmod +w /etc/sudoers                                                                 &&\
    echo 'haedong    ALL=(ALL)       NOPASSWD: ALL' >> /etc/sudoers                       &&\
    echo '$APP_USER    ALL=(ALL)       NOPASSWD: ALL' >> /etc/sudoers                     

COPY --chown=777:777 files/.bashrc /home/haedong/.bashrc
COPY --chown=1000:1000 files/.bashrc /home/$APP_USER/.bashrc
COPY --chown=1:1 files/.bashrc /root/.bashrc

# to fun python scripts
RUN dnf install -y python3.11 python3.11-devel python3.11-libs python3.11-pip             &&\
    dnf clean all                                                                         &&\
    ln -s /usr/bin/python3.11 /usr/bin/python                                             &&\
    ln -s /usr/bin/pip3.11 /usr/bin/pip                                                   
    

# create app directory
RUN mkdir /opt/apps/healthz && ln -s /opt/apps/healthz /opt/healthz                       &&\
    chown -R 1000:1000 /opt/apps/healthz /opt/healthz

# script copy
COPY chown=1000:1000 app /opt/apps/healthz/app
COPY files/entrypoint.sh /opt/apps/healthz/entrypoint.sh

# set working directory
WORKDIR /opt/apps

# entrypoint
ENTRYPOINT ["/opt/healthz/entrypoint.sh"]

# ports to open
EXPOSE 8080,65535
