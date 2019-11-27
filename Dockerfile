# Forked from Jakob Smretschnig <jakob.smretschnig@tum.de>, based on
# docker-image by Bo Gao <bogao@dcs.warwick.ac.uk> 
# in collaboration with Ljube B. <@tum.de>

# Use ubuntu as a parent image - 18.04 has LTS
FROM ubuntu:18.04

LABEL Description = "Emission Simulation, Prediction and Visualization"
ENV DEBIAN_FRONTEND=noninteractive 

# Install system dependencies
RUN apt-get -qq update && apt-get -qq install \
    cmake g++ libxerces-c-dev libfox-1.6-dev libgdal-dev libproj-dev libgl2ps-dev swig git \
    ffmpeg \
    wget \
    sudo \
    xorg

## Install SUMO
RUN git clone --recursive https://github.com/eclipse/sumo --verbose --progress && mkdir sumo/build/cmake-build
WORKDIR /sumo/build/cmake-build 
RUN cmake ../.. && make -j$(nproc)

ENV SUMO_HOME /sumo

################# END OF 'COMMON' IMAGE ####################

############################################################
######################## API ###############################
############################################################

RUN sudo apt-get install -qq \
    python3-dev \
    python3-pip \
    python3-rtree

RUN apt-get -qq install python3.7 python3.7-dev curl python3-distutils && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.7 get-pip.py
RUN cp /usr/bin/python3.7 /usr/bin/python

WORKDIR /
# Setting up poetry
COPY poetry.lock /
COPY pyproject.toml .
RUN pip3 install poetry && \
    poetry config settings.virtualenvs.create false && \
    poetry install -v

COPY . /

EXPOSE 8000
EXPOSE 4040

CMD gunicorn app.main:app --timeout 500 --workers 5 -k uvicorn.workers.UvicornWorker -b 0.0.0.0

