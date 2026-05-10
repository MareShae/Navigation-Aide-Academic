# Navigation Aide - Academic

The Navigation Aide is a wearable device that processes visual information and relays its depth information through audio feedback to allow visually impaired individuals to be aware of their surroundings.

![An accurate depiction of the prototype in CAD](/assets/cad_model.png)


## Architecture
The project is implemented as a distributed architecture to offload compute-intense tasks from the RPi client to a localized server on an Asus Vivobook 14 via sockets. 

![The algorithm](/assets/algorithm.png)

It starts from the RPi, which, paired with a 3D printed frame, a RPi Camera Module and a set of headphones, captures an image and uploads it to the server.

The server uses the [MiDaS - Monocular Depth Estimation](https://github.com/isl-org/MiDaS.git) machine learning model to infere the depth of every pixel in the image. It then segments the inference based on intensity gradients, and places bounding boxes of each as regions of interest (ROI). The server finally sends all the ROI to the client.

|![The server process](/assets/server_process.png)|
|:--:|
|*From left to right: (a) original image, (b) depth inference, (c) coloured segments and edges in white*|

The client converts the ROI from the inference into spatial audio by simulating it as a physical location within the confines of the captured image and manipulating its frequency. Physical location is at the center of its boundary and frequency is directly proportional to the boundary length. Depth attenuation and azimuth, to infere the orientation relative to the center of the image, are also applied to the left and right audio channels. The resulting audio is played through the headphones.


## Setup
The server-side depends on isl-org/MiDaS. To install on the server, in a terminal:
```
git clone https://github.com/MareShae/Navigation-Aide-Academic.git
cd Navigation-Aide-Academic

git submodule update --init --recursive

python3 -m venv venv
venv/bin/pip -m install -r ServerPC/requirements.txt
```

To unintall on server:
```
rm -rf Navigation-Aide-Academic
```

In a terminal on the client:
```
git clone https://github.com/MareShae/Navigation-Aide-Academic.git
cd Navigation-Aide-Academic

chmod +x ClientRPi/requirements.sh
chmod +x ClientRPi/naviaidemgr

ClientRPi/requirements.sh
sudo naviaidemgr --install
```

To unintall on client:
```
sudo naviaidemgr --uninstall
rm -rf Navigation-Aide-Academic
```


## ℹ️
This project utilizes [MiDaS](https://github.com/isl-org/MiDaS.git) depth estimation model, by Intel Labs for image processing, as a submodule; See .gitmodules. It was sponsored by the University of Victoria and Co-operative Education and Work-Integrated Learning (CEWIL). Its successful completion was a core requirement for ECE 499. Three students developed Navigation Aide, and I was responsible for all code in this repository.
