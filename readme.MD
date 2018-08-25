# Automatic Cone Photoreceptor Localisation with MDRNNs

This repo contains an implementation of the method described in [this paper](https://www.osapublishing.org/boe/abstract.cfm?uri=boe-9-9-4317). Please cite the paper if you use the code.
```
@article{Davidson:18,
author = {Benjamin Davidson and Angelos Kalitzeos and Joseph Carroll and Alfredo Dubra and Sebastien Ourselin and Michel Michaelides and Christos Bergeles},
journal = {Biomed. Opt. Express},
keywords = {Image processing; Image quality; Ophthalmic imaging; Optical imaging; Scanning laser ophthalmoscopy; Wavefront aberrations},
number = {9},
pages = {4317--4328},
publisher = {OSA},
title = {Fast adaptive optics scanning light ophthalmoscope retinal montaging},
volume = {9},
month = {Sep},
year = {2018},
url = {http://www.osapublishing.org/boe/abstract.cfm?URI=boe-9-9-4317},
doi = {10.1364/BOE.9.004317},
}




```

## Getting Started
To install and use requires:
* Python 3
* pip

### Installing
1. Download the git repository to a folder of your choice, /path/to/code/autoMontager

2. Install Python package using pip. Ubuntu: ```pip install /path/to/code/autoMontager```; Windows```python -m pip install /path/to/code/ConeDetector```

### Using

* Run from command line 

```
auto_montage -c path/to/config.yaml
```

## Features
The config.yaml should contain

* path to folder of tiles
* path to nominal locations .xlsx sheet (example included)
* where to save the generated photoshop script
* which eye
* naming convention between tiles




