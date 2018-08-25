from . import multi_modal_image

import os
import csv
import numpy as np
import xlrd
import re

class FilePlumber:
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
        self.nominal_dictionary = self.build_nominal_dictionary(excell)
        
        

        # save all three image filenames to a list
        # along with the actual nominal position
        image_names = self.build_multimodal_list()
        combined_modality = self.combine_images(image_names)
        self.filenames_and_position = self.get_nominal(combined_modality)
        

    def build_nominal_dictionary(self, excell):
        """
            Read AOSLO processing notes, in the styke
            kept by Moorfields. Construct a dictionary
            mapping movie_numbers to locations

            excell:
                path_to_file
            nominal_dict:
                dict[movie_number] = np.array([y, x])

        """
        workbook = xlrd.open_workbook(excell)
        worksheet = workbook.sheet_by_index(0)

        # Assumes starting locations are
        # row 12, col 2 and row 12, col 10
        movie_num_loc = 13, 1
        movie_location = 13, 2
        nominal_dictionary = {}
        still_movies = True
        while still_movies:
            try:
                movie_num = worksheet.cell(*movie_num_loc).value
                movie_loc = str(worksheet.cell(*movie_location).value)
            except IndexError:
                break

            try:
                int(movie_num)
            except ValueError:
                break
    
            if not movie_loc:
                break
                
            movie_num_loc = movie_num_loc[0] + 1, movie_num_loc[1]
            movie_location = movie_location[0] + 1, movie_location[1]
            nominal_dictionary[int(movie_num)] = movie_loc
        # convert to locations
        def posToLoc(pos):
            """transforms text to nominal location"""

            # make lower case and extract an digits in the string
            pos = pos.lower()
            digits = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", pos)]
            # if there are digits it means it is of the form
            # with I,S,T,I so we need to extract the letters
            # as well.
            if digits:

                # remove everything that is not a coordinate letter
                pos = re.sub('[^nsti]', '', pos)
                letters = pos

            # mapping from string to coordinates
            # some flip if different eyes
            pos_map = {
                'c': (0.0, 0.0),
                'trc':(0.6, 0.6),
                'mre':(0.0, 0.6),
                'brc':(-0.6, 0.6),
                'mbe':(-0.6, 0.0),
                'blc':(-0.6, -0.6),
                'mle':(0.0, -0.6),
                'mrc':(0.0, 0.6),
                'tlc':(0.6, -0.6),
                'mte':(0.6, 0.0),
                'centre': (0. ,0.),
                'center':(0.,0.),
                's':(1., 0.),
                'i':(-1.,0.),
                'n':(0., -1.) if self.eye=='OD' else (0., 1.),
                't':(0., 1.) if self.eye=='OD' else (0., -1.)
            }

            # if there were any digits then it is of the coordinate
            # form and we need to do some multiplication. Otherwise 
            # just straight replace
            if digits:
                location = np.zeros([2])
                for k in range(len(letters)):
                    location += digits[k]*np.array(pos_map[letters[k]])
            else:
                try:
                    location = np.array(pos_map[pos])
                except KeyError:
                    print('Warning: movie had unrecognised position {}'.format(pos))
                    print('Assuming central')
                    location = np.zeros([2])

            return location

        # nominaldict[movie number] = location
        for key in nominal_dictionary:
            nominal_dictionary[key] = posToLoc(nominal_dictionary[key])

        return nominal_dictionary

    def build_multimodal_list(self,):
        """flat list with all tifs in a directory"""

        def filterImages(fname):
            """filter tifs"""
            extension = fname.split('.')[-1]
            if extension=='tif':
                return True
            else:
                return False

        # all images in a directory
        # only filename not full path
        file_list = filter(
            filterImages, 
            os.listdir(self.directory))
            
        return list(file_list)

    def combine_images(self, image_names):
        """
            Take flat list of image_paths. Triple them
            with their corresponding, channels: confocal
            avg, and split.
        """

        # there should be a number of images divisible by 3
        list_length = len(image_names)
        assert list_length%3==0

        # will eventually form our output
        tripled_images = [None]*(list_length//3)

        def getType(fname):
            """returns type of channel from fname"""
            for key in self.name_convention:
                val = self.name_convention[key]
                if val in fname:
                    return key
            raise ValueError('Found fname %s without valid channel name' %(fname))

        def getOtherTwoAndDelete(current_type, current_fname, triple, types):
            """
                given a filename we select the other two corresponding images 
                with the other channel types and fill a dictionary with these
                values. Tripling the images together

                Inputs
                    channel type
                    name
                    partially filled dictionary triple
                    all channel types
                
            """

            # only keep the two channel types we don't have yet
            otherTypes = filter(lambda x: not x==current_type, types)

            # for each unlinked channel type make the new path, and
            # ensure it is in the list. If it is delete it from the
            # list, if not raise an error
            for otherType in otherTypes:

                # build new image name and full path
                newFname = current_fname.replace(
                    self.name_convention[current_type], 
                    self.name_convention[otherType])
                triple[otherType] = os.path.join(self.directory, newFname)
                
                # find value in list and delete
                found = False
                for idx, val in enumerate(image_names):
                    if val==newFname:
                        del image_names[idx]
                        found = True
                        break

                # couldnt find the value in list so no multimodal
                if not found:
                    raise ValueError(
                        'Could not find %s\n In %s Tried to replace %s with %s' %(newFname, self.directory, current_type, otherType ))
            return triple

        # Go through flat list of all names and triple everything
        types = set(self.name_convention.keys())
        idt = 0
        while True:

            # currently tripled images
            triple = {'confocal':None, 'split':None, 'avg':None}

            # take first image in list and add to the triple
            # following this delete from list
            current_fname = image_names[0]
            current_type = getType(current_fname)
            triple[current_type] = os.path.join(self.directory, current_fname)
            del image_names[0]

            # Using the first added image, get the other two images
            triple = getOtherTwoAndDelete(current_type, current_fname, triple, types)
            tripled_images[idt] = triple
            idt += 1

            # paired all images
            if len(image_names)==0:
                break

        return tripled_images

    def get_nominal(self, combined_modality):
        """
            With the tripled images, extract their movie_numbers
            and attach their nominal positions.
        """

        # output list of dictionaries
        fnames_with_pos = []

        def getMovieNum(multimodal):
            """
                extract the movie_number from an image name.
                assumes that the movie number 0000 appears as
                    ******self.name_convention['confocal']_0000*************
            """
            conf_name = self.name_convention['confocal']
            fname = multimodal['confocal']
            idx = fname.index(conf_name + '_') + len(conf_name + '_')
            num_str = fname[idx:idx+4] if fname[idx:idx+4]=='0000' else fname[idx:idx+4].lstrip('0')
            movie_num = int(num_str)
            return movie_num
            
        def getPos(multimodal):
            movie_num = getMovieNum(multimodal)
            try:
                multimodal['nominal'] = self.nominal_dictionary[movie_num]
            except KeyError:
                print('Warning: movie {} has no position'.format(movie_num))
                multimodal['nominal'] = np.zeros([2])
            return multimodal

        for multimodal in combined_modality:
            with_pos = getPos(multimodal)
            fnames_with_pos.append(with_pos)

        return fnames_with_pos

    def __getitem__(self, i):
        return self.filenames_and_position[i]

    def __len__(self,):
        return len(self.filenames_and_position)

    def get_as_list(self,):
        """
            constructs MultiModalImage from the fnames
            and positions. Returning a list of these objects
        """
        mm_list = []
        for idx in range(len(self.filenames_and_position)):
            multiImage = self.filenames_and_position[idx]
            mmImage = multi_modal_image.MultiModalImage(
                multiImage['confocal'], 
                multiImage['split'], 
                multiImage['avg'], 
                multiImage['nominal'])
            mm_list.append(mmImage)

        return mm_list

    @staticmethod
    def get_data(fldr):
        data = []
        for dataset in os.listdir(fldr):
            d = dict()
            patient_folder = os.path.join(fldr, dataset)
            d['directory'] = os.path.join(patient_folder, 'processed')
            d['naming'] = {'confocal':'confocal', 'split':'split_det', 'avg':'avg'}
            d['excell'] = os.path.join(patient_folder, [x for x in os.listdir(patient_folder) if x[-1]=='x'][0])
            d['photoshopDirectory'] = patient_folder
            d['eye'] = 'OS'
            data.append(d)
        return data