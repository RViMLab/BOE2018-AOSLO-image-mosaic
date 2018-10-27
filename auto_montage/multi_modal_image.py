from . import utils
from . import features

import numpy as np


class MultiModalImage:
    index = {'split':0, 'confocal':1, 'avg':2}

    def __init__(self, confocal, split, avg, nominal_position, fov):
        """
            store names, nominal position and images as a single
            numpy tensor [height, width, channel]
        """
        self.fov = fov
        self.split_fname = split
        self.confocal_fname = confocal
        self.avg_fname = avg
        split = utils.load_from_fname(split)
        confocal = utils.load_from_fname(confocal)
        avg = utils.load_from_fname(avg)
        self.multimodal_im = np.stack([split, confocal, avg], axis=2)
        self.nominal_position = nominal_position

        self.keypoints = {'split':None, 'confocal':None, 'avg':None}
        self.descriptors = {'split':None, 'confocal':None, 'avg':None}

    def get_confocal(self,):
        return self.multimodal_im[:,:,MultiModalImage.index['confocal']]

    def get_split(self,):
        return self.multimodal_im[:,:,MultiModalImage.index['split']]

    def get_avg(self,):
        return self.multimodal_im[:,:,MultiModalImage.index['avg']]

    def get_split_name(self,):
        return self.split_fname

    def get_confocal_name(self,):
        return self.confocal_fname

    def get_avg_name(self,):
        return self.avg_fname

    def get_nominal(self,):
        return self.nominal_position

    def get_image_and_name(self, mntge_type):
        if mntge_type == 'confocal':
            src_img = self.get_confocal()
            src_name = self.get_confocal_name()
        elif mntge_type == 'split':
            src_img = self.get_split()
            src_name = self.get_split_name()
        elif mntge_type == 'avg':
            src_img = self.get_avg()
            src_name = self.get_avg_name()
        else:
            raise ValueError('No type named {}'.format(mntge_type))
        return src_img, src_name

    def calculate_orb(self,):
        """calculate and set the descriptors"""
        for modality in self.keypoints.keys():
            image = self.multimodal_im[:,:,MultiModalImage.index[modality]]
            kps, desc = features.compute_kps_desc(image)
            self.keypoints[modality] = kps
            self.descriptors[modality] = desc



