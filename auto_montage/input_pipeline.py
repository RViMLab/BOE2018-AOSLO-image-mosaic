from . import multi_modal_image

import os
import csv
import numpy as np
import xlrd
import re


class InputPipeline:
    """
        Triples images together, confocal, avg, and split. Returning
        a list of MultiModalImage objects.
    """

    def __init__(self, directory, excell, name_convention, eye):
        """
            directory: where all your images live
            excell: path to excell file
            name_convention: how modalities are distinguished
                             in filenames
            eye: which eye 
            self.directory
            self.excell
            self.name_convention
            self.eye
            self.filenames_and_position: 
                list of dictionaries with paths of all modalities
                and the nominal position extracted from the excell 
                file

        """

        # build dict with 
        # self.nominal_dictionary[movie_number] = nominal_position
        self.eye = eye
        self.directory = directory
        self.name_convention = name_convention
        self.position_map = self.build_position_map()
        self.nominal_dictionary = self.build_nominal_dictionary(excell)

        # save all three image filenames to a list
        # along with the actual nominal position
        image_names = self.get_all_tifs_in_dir()
        combined_modality = self.combine_images(image_names)
        self.triples_by_fov = self.get_nominal(combined_modality)

    def build_position_map(self):
        pos_map = {
            'c': (0.0, 0.0),
            'trc': (0.6, 0.6),
            'mre': (0.0, 0.6),
            'brc': (-0.6, 0.6),
            'mbe': (-0.6, 0.0),
            'blc': (-0.6, -0.6),
            'mle': (0.0, -0.6),
            'mrc': (0.0, 0.6),
            'tlc': (0.6, -0.6),
            'mte': (0.6, 0.0),
            'centre': (0., 0.),
            'center': (0., 0.),
            's': (1., 0.),
            'i': (-1., 0.),
            'n': (0., -1.) if self.eye == 'OD' else (0., 1.),
            't': (0., 1.) if self.eye == 'OD' else (0., -1.)
        }
        return pos_map

    def convert_xlsx_pos_to_coord(self, text_location):
        """transforms text to nominal location"""
        try:
            text_location = text_location.lower()
        except AttributeError:
            print('given location in excell file is not string: {}'.format(text_location))
        digits_in_text_location = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", text_location)]

        # contains digits then its coordinate form
        # we strip the letters which are just a basis
        # and add and multiply according to digits
        if digits_in_text_location:
            # remove everything that is not a coordinate letter
            text_location = re.sub('[^nsti]', '', text_location)
            letters = text_location
            location = np.zeros([2])
            for k in range(len(letters)):
                location += digits_in_text_location[k] * np.array(self.position_map[letters[k]])
        # No digits: either a mistake or one of the existing names
        # in self.position_map
        else:
            try:
                location = np.array(self.position_map[text_location])
            except KeyError:
                print('Warning: movie had unrecognised position {}'.format(text_location))
                print('Assuming central')
                location = np.zeros([2])

        return location

    def build_nominal_dictionary(self, excell):
        movie_nums, movie_locs, fovs = self.read_xlsx(excell)
        nominal_dictionary = {movie_nums[i]: (movie_locs[i], fovs[i]) for i in range(len(movie_nums))}
        return nominal_dictionary

    def read_xlsx(self, excell):

        workbook = xlrd.open_workbook(excell)
        worksheet = workbook.sheet_by_index(0)

        movie_nums = worksheet.col_values(0)
        movie_locs = worksheet.col_values(1)
        fovs = worksheet.col_values(2)
        movie_nums = [int(x) for x in movie_nums]
        movie_locs = [self.convert_xlsx_pos_to_coord(x) for x in movie_locs]
        fovs = [float(x) for x in fovs]
        assert len(movie_nums) == len(movie_locs)
        assert len(movie_locs) == len(fovs)

        return movie_nums, movie_locs, fovs

    def get_all_tifs_in_dir(self, ):
        tif_fnames = [x for x in os.listdir(self.directory) if x[-4:] == '.tif']
        tif_paths = [os.path.join(self.directory, x) for x in tif_fnames]
        return tif_paths

    def channel_from_fname(self, fname):
        for key in self.name_convention:
            val = self.name_convention[key]
            if val in fname:
                return key
        raise ValueError('Found fname %s without valid channel name' %(fname))

    def _triple_first_image(self, image_names):
        triple = {}
        channels = set(self.name_convention.keys())
        curr_to_triple = image_names[0]
        channel_type = self.channel_from_fname(curr_to_triple)
        triple[channel_type] = curr_to_triple
        image_names.remove(curr_to_triple)
        remaining_channels = (channels - {channel_type})
        for other_channel in remaining_channels:
            other_channel_fname = curr_to_triple.replace(
                self.name_convention[channel_type],
                self.name_convention[other_channel], )
            triple[other_channel] = other_channel_fname
            image_names.remove(other_channel_fname)

        return image_names, triple

    def combine_images(self, image_names):
        """Triple flat image list so tripled with other channels, conf, split, avg"""

        list_length = len(image_names)
        assert list_length%3==0, 'Number of images not divisible by three'

        tripled_images = []
        while len(image_names) > 0:
            image_names, triple = self._triple_first_image(image_names)
            tripled_images.append(triple)

        return tripled_images

    def movie_num_from_triple(self, triple):
        """
            extract the movie_number from an image name.
            assumes that the movie number 0000 appears as
                ******self.name_convention['confocal']_0000*************
        """
        conf_name = self.name_convention['confocal']
        fname = triple['confocal']
        idx = fname.index(conf_name + '_') + len(conf_name + '_')
        num_str = fname[idx:idx + 4] if fname[idx:idx + 4] == '0000' else fname[idx:idx + 4].lstrip('0')
        movie_num = int(num_str)
        return movie_num

    def attach_location_to_triple(self, triple):
        movie_num = self.movie_num_from_triple(triple)
        try:
            triple['nominal'] = self.nominal_dictionary[movie_num][0]
            triple['fov'] = self.nominal_dictionary[movie_num][1]
        except KeyError:
            print('Warning: when trying to attach locations to triples')
            print('movie {} had no (position or FOV)'.format(movie_num))
            print('Assuming central and continuing')
            triple['nominal'] = np.zeros([2])
        return triple

    def get_nominal(self, triples):
        triples_by_fov = {}
        for triple in triples:
            with_pos = self.attach_location_to_triple(triple)
            if with_pos['fov'] in triples_by_fov.keys():
                triples_by_fov[with_pos['fov']].append(with_pos)
            else:
                triples_by_fov[with_pos['fov']] = [with_pos]

        return triples_by_fov

    def __getitem__(self, i):
        return self.triples_by_fov[i]

    def __len__(self,):
        return len(self.triples_by_fov)

    def as_multi_modal_objects(self, ):
        mm_dict = {}
        for fov in self.triples_by_fov:
            mm_dict[fov] = [
                multi_modal_image.MultiModalImage(
                    triple['confocal'],
                    triple['split'],
                    triple['avg'],
                    triple['nominal'],
                    fov)
                for triple in self.triples_by_fov[fov]
            ]
        return mm_dict