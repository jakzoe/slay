# docker build -t laserdocker:release . && docker build -t laserdocker:debug --target debug .
# docker system prune # -a for EVERYTHING

FROM debian:latest AS base

RUN apt -y update && apt -y upgrade
RUN apt -y install libssl-dev openssl wget build-essential zlib1g-dev libffi-dev libcairo2-dev libgirepository1.0-dev libopencv-dev libusb-1.0-0-dev usbutils udev
RUN apt -y install mesa-utils libgtk-3-dev
# needed for building for ipython
RUN apt-get -y install libsqlite3-dev

# This is needed for the stellarnet driverLibs. Using conda would work too of course. 
WORKDIR /usr/src
RUN wget https://www.python.org/ftp/python/3.10.9/Python-3.10.9.tgz
RUN tar zxvf Python-3.10.9.tgz
WORKDIR /usr/src/Python-3.10.9
RUN ./configure --enable-optimizations
RUN make install -j4

RUN mkdir -p /etc/udev/rules.d/

# not needed at the moment, since everything is run by root anyway
# grant access to the spectrometer
RUN bash -c "echo 'SUBSYSTEMS==\"usb\", ATTRS{idVendor}==\"04b4\", ATTRS{idProduct}==\"8613\" GROUP=\"uucp\", MODE=\"0666\"' > /etc/udev/rules.d/50-spectro.rules"
# apparently, the spectrometer's library changes the device to "0bd7:a012 Andrew Pargeter & Associates USB2EPP"
RUN bash -c "echo 'SUBSYSTEMS==\"usb\", ATTRS{idVendor}==\"0bd7\", ATTRS{idProduct}==\"a012\" GROUP=\"uucp\", MODE=\"0666\"' >> /etc/udev/rules.d/50-spectro.rules"

ARG INSTALL_PATH="/root/slay"
RUN echo "mount your code/data directory to ${INSTALL_PATH}, e.g. docker run -v /home/user/slay/myproject:${INSTALL_PATH} laserdocker"
RUN mkdir -p ${INSTALL_PATH}

# see https://github.com/AlfredoSequeida/hints/issues/44
# RUN apt -y install libgirepository-2.0-dev

# PyGObject as an alternative to the larger matplotlib backend tkinter:
RUN /usr/local/bin/pip3 install pyusb pyserial numpy matplotlib PyGObject==3.50.0 SciencePlots pylablib opencv-python
# SciencePlots is able to use LaTeX (can be disabled using 'no-latex')
RUN apt-get -y install dvipng texlive-latex-extra texlive-fonts-recommended cm-super

RUN /usr/local/bin/pip3 install ipython

COPY bin/stellarnet_driverLibs/ /usr/local/bin/stellarnet/driverLibs
ENV PYTHONPATH="/usr/local/bin/stellarnet"
#ENV IN_DOCKER=True

# WORKDIR $INSTALL_PATH/slay/
WORKDIR $INSTALL_PATH

FROM base AS debug

RUN /usr/local/bin/pip3 install debugpy
RUN /usr/local/bin/pip3 install pip-licenses

# pip-licenses --python=/usr/local/bin/python3;
ENTRYPOINT ["/bin/sh", "-c", "/usr/local/bin/python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client examples/run_measurement.py"]


FROM base AS release

# finding the src dir
ENV PYTHONPATH="$PYTHONPATH:$INSTALL_PATH"
# exec form
#ENTRYPOINT ["/usr/local/bin/python3", "nkt.py"]
ENTRYPOINT ["/usr/local/bin/python3", "examples/run_measurement.py"]

# # shell form
# SHELL ["/bin/bash", "-c"]
# ENTRYPOINT /usr/local/bin/python3 laser_messungen.py
