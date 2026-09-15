FROM python:3.13-slim-trixie AS base

ARG INSTALL_PATH="/root/slay"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin
ENV PYTHONPATH="/usr/local/bin/stellarnet:${INSTALL_PATH}"

RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=tmpfs,target=/var/lib/dpkg/updates \
    # dpkg tries to delete this in the end
    #--mount=type=tmpfs,target=/var/lib/dpkg/tmp.ci \
    --mount=type=tmpfs,target=/var/log/apt \
    --mount=type=tmpfs,target=/var/tmp \
    --mount=type=tmpfs,target=/tmp \
       apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        \
        libusb-1.0-0-dev \
        usbutils \
        # udevadm needed for device discovery
        udev \
        \
        # web downloads
        openssl \
        ca-certificates \
        wget \
        \
        # LaTeX / plotting
        dvipng \
        texlive-latex-base \
        texlive-latex-extra \
        cm-super \
        fontconfig \
        \
        tzdata

# make LaTeX fonts available to other software
RUN mkdir -p /usr/share/fonts/truetype/latex \
    && find /usr/share/texlive/texmf-dist/fonts/ -name "*.ttf" -o -name "*.otf" \
       -exec ln -s {} /usr/share/fonts/truetype/latex/ \; \
    && fc-cache -f -v


RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "${TZ}" > /etc/timezone

RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=tmpfs,target=/tmp \
        wget https://packages.microsoft.com/config/debian/13/packages-microsoft-prod.deb \
    -O /tmp/packages-microsoft-prod.deb \
&& dpkg -i /tmp/packages-microsoft-prod.deb \
&& apt-get update \
&& apt-get install -y --no-install-recommends dotnet-sdk-8.0

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
        #--only-binary=:all: \
        pyusb \
        pyserial \
        numpy \
        matplotlib \
        SciencePlots \
        pylablib \
        opencv-python-headless \
        ipython \
        ruptures \
        pythonnet \
        # needed for WebAgg
        tornado

COPY bin/stellarnet_driverLibs/ /usr/local/bin/stellarnet/driverLibs/
COPY thorlabs-cct/ /root/thorlabs-cct/
COPY bin/pyCCT/ /root/thorlabs-cct/pyCCT/

RUN mkdir -p "${INSTALL_PATH}"

WORKDIR ${INSTALL_PATH}

FROM base AS debug

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install debugpy pip-licenses

COPY debug_entrypoint.sh /debug_entrypoint.sh

ENTRYPOINT ["sh", "/debug_entrypoint.sh"]


FROM base AS release

ENTRYPOINT ["python", "examples/run_measurement.py"]