import math
import numpy as np
import csv
import matplotlib

import os
from scipy.sparse import csgraph
from scipy import ndimage
import random
from PIL import Image

class MontageBuilder:
    COMPONENT_BUILT = -1

    def __init__(self, transformation_finder, evaluate=False):
        self.matched = transformation_finder.matched
        self.translation = transformation_finder.translations
        self.global_translation = np.zeros_like(self.translation)
        self.mm_images = transformation_finder.mmList
        self._num_im = len(self.mm_images)
        
    def connnected_components(self,):
        graph = np.zeros([self._num_im,self._num_im], dtype=np.bool)
        for i in range(self.matched.shape[0]):
            graph[i, self.matched[i]] = True
        n, labels = csgraph.connected_components(graph, directed=False, return_labels=True)
        return n, labels

    def construct_all_montages(self,):
        number_components, labels = self.connnected_components()
        disjoint_montages = []

        for component in range(number_components):
            indices = np.argwhere(labels==component)
            transformations, indices = self.construct_component(indices, component)
            disjoint_montages.append((transformations, indices))
        return disjoint_montages

    def _get_pairwise(self, indices):
        # get all pairwise connections
        connected_to = dict()
        original_image = None
        for dst_img in indices:
            connected_to[dst_img] = []
            for src_img in indices:

                # find images which map to dst_img
                if self.matched[src_img]==dst_img:
                    connected_to[dst_img].append(src_img)

                # get fixed image
                if self.matched[dst_img]==dst_img:
                    original_image = dst_img

            # delete dict entry if empty
            if len(connected_to[dst_img])==0:
                connected_to.pop(dst_img, None)

        return connected_to, original_image

    def _choose_next_dst(self, current_dst, connected_to):
        for key in connected_to.keys():
            if key==current_dst:
                continue
            if key in connected_to[current_dst]:
                return key, True
        return None, False

    def update_local_transformation(self, directly_connected, global_ref):

        def recursiveTranslation(reference, global_trans):

            # ending condition, which will always be met
            # as this is a connected component
            if reference in directly_connected[global_ref]:
                return global_trans + self.translation[reference, global_ref]
                

            # find any element which contains local ref as src
            # and align the ref to this, then look for how to
            # align the new ref to global ref

            for ref in directly_connected:
                src_ims = directly_connected[ref]
                if reference in src_ims:
                    global_trans += self.translation[reference, ref]
                    global_trans = recursiveTranslation(ref, global_trans)
                    break
            return global_trans

        global_trans_dict = dict()
        for ref in directly_connected:
            src_ims = directly_connected[ref]
            global_trans = np.array([0.,0.])
            global_trans = recursiveTranslation(ref, global_trans)
            global_trans_dict[ref] = global_trans

        for ref in directly_connected:
            src_ims = directly_connected[ref]
            for src in src_ims:
                self.translation[src, ref] += global_trans_dict[ref]

    def get_transformation(self, indices):
        transformations = []
        for src_id in indices:
            row = dict()

            # file names
            confocal = self.mm_images[src_id].get_confocal_name()
            split = self.mm_images[src_id].get_split_name()
            avg = self.mm_images[src_id].get_avg_name()

            # translation
            dst_id = self.matched[src_id]
            t = self.translation[src_id, dst_id]
            y, x = t[0,0], t[0,1]

            # put into dict and write
            row['confocal'] = confocal
            row['split'] = split
            row['avg'] = avg
            row['transy'] = y
            row['transx'] = x
            row['h'] = self.mm_images[src_id].get_confocal().shape[0]
            row['w'] = self.mm_images[src_id].get_confocal().shape[1]

            transformations.append(row)
        return transformations

    def construct_component(self, indices, idx):
        # make into iterable list
        indices = list(indices.ravel())

        # get first pairwise connections
        directly_connected, global_ref = self._get_pairwise(indices)

        # construct gobal transformation
        self.update_local_transformation(directly_connected, global_ref)

        # write transformation to file
        transformations = self.get_transformation(indices)

        return transformations, indices

    def transform_box(self, src, dst, box):
        transform = self.translation[src, dst]
        return box + transform

    def _get_global_box(self, indices):
        """bounding box size for a chunk after making transformation global"""
        global_x_min = np.infty
        global_x_max = -np.infty
        global_y_min = np.infty
        global_y_max = -np.infty
        for src_id in indices:
            # get vals
            src_img = self.mm_images[src_id]
            dst_id = self.matched[src_id]
            h, w = src_img.get_confocal().shape

            # transform box and find values
            bounding_box = np.array([[0,0], [0, h-1], [w-1, 0], [w-1, h-1]])
            transfor_box = self.transform_box(src_id, dst_id, bounding_box)
            x_min, y_min = np.min(transfor_box, axis=0)
            x_max, y_max = np.max(transfor_box, axis=0)

            # update global box
            global_x_min = x_min if x_min < global_x_min else global_x_min
            global_y_min = y_min if y_min < global_y_min else global_y_min
            global_x_max = x_max if x_max > global_x_max else global_x_max
            global_y_max = y_max if y_max > global_y_max else global_y_max

        return int(global_x_min), int(global_x_max), int(global_y_min), int(global_y_max)

    def setup_folders(self, indice_list, subject):
        eval_directory = '/media/benjamin/Seagate Backup Plus Drive/montageWithPiece'
        directory = os.path.join(eval_directory, subject)
        os.makedirs(directory)

        for idx, val in enumerate(indice_list):
            for modality in ['confocal', 'split', 'avg']:
                new_dir = os.path.join(directory, str(idx), modality)
                os.makedirs(new_dir)

    def build_fname(self, subject, mntge_type, idx, fname):
        # build save path
        eval_directory = '/media/benjamin/Seagate Backup Plus Drive/montageWithPiece'
        save_path = os.path.join(eval_directory, subject, str(idx), mntge_type, fname)
        return save_path

    def saveImWithAlpha(self, im, alpha, subject, mntge_type, idx, fname):

        fname = fname.split('/')[-1]
        save_path = self.build_fname(subject, mntge_type, idx, fname)

        # convert image to pil LA image
        im = np.uint8(im)
        im = Image.fromarray(im)
        im = im.convert('LA')

        # convert alpha mask to L
        alpha = np.uint8(alpha*255)
        alpha_im = Image.fromarray(alpha)
        alpha_im = alpha_im.convert('L')

        # build and save
        im.putalpha(alpha_im)
        im.save(save_path)

    def save_montage(self, montage, subject, mntge_type, idx):
        save_path = self.build_fname(subject, mntge_type, idx, 'full.tiff')

        # convert image to pil LA image
        montage = np.uint8(montage)
        im = Image.fromarray(montage)
        im.save(save_path)

    def save_pieces(self, indices_list, subject):

        # setup all folders for the subject montage
        self.setup_folders(indices_list, subject)

        for idx, indices in enumerate(indices_list):

            # build global coordinates
            gx_min, gx_max, gy_min, gy_max = self._get_global_box(indices)
            grid_x, grid_y = np.meshgrid(
                np.arange(gx_min, gx_max), 
                np.arange(gy_min, gy_max),
                )
            montage = np.zeros([gy_max-gy_min, gx_max-gx_min])

            for mntge_type in ['confocal', 'split', 'avg']:

                for src_id in indices:
                    src_img, src_name = self.mm_images[src_id].get_image_and_name(mntge_type)
                    dst_id = self.matched[src_id]

                    # mask to form alpha channel
                    src_mask = np.ones(src_img.shape)
                    
                    # actual translation
                    t = self.translation[src_id, dst_id]

                    # move image and mask
                    warped_image = ndimage.map_coordinates(
                        src_img,
                        [grid_y-t[0,1], grid_x-t[0,0]],
                        order=3,
                        cval=0.0,)

                    warped_mask = ndimage.map_coordinates(
                        src_mask,
                        [grid_y-t[0,1], grid_x-t[0,0]],
                        order=1,
                        cval=0.0,)

                    self.saveImWithAlpha(warped_image, warped_mask, subject, mntge_type, idx, src_name)
                    montage = np.where(warped_mask > 0, warped_image, montage)

                self.save_montage(montage, subject, mntge_type, idx)
                    
                    
                    
        





        