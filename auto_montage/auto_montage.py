from . import transformation_finder
from . import montage_builder
from . import file_plumber
from . import script_maker

import yaml

import os
from time import time
import matplotlib

def main(config_path, evaluate=False, batch=False):

    
    if not batch:
        with open(config_path, 'r') as stream:
            try:
                config_info = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        data = [config_info]
    else:
        data = file_plumber.FilePlumber.get_data(config_path)

    for config_info in data:
        print(config_info['directory'])
        s = time()

        # get config
        naming = config_info['naming']
        directory = config_info['directory']
        excell = config_info['excell']
        photoshop_directory = config_info['photoshopDirectory']
        eye = config_info['eye']

        # gets all our files matched with different modalities
        print('Getting all files ...')
        m = file_plumber.FilePlumber(directory, excell, naming, eye)
        mmList = m.get_as_list()

        # calculates all keypoints and descriptors
        # then constructs a global registration out
        # of pairwise registrations
        print('Computing keypoints and descriptors ...')
        tf = transformation_finder.TransformationFinder(mmList)
        tf.compute_kps_desc()

        print('Building registrations ...')
        tf.compute_pairwise_registrations()

        print('Finished!')
        print(config_info['directory'])
        print(time() - s)

        # list of lists. The top layer is disjoint 
        # montages, followed by the transformations
        # and file names neededd
        mb = montage_builder.MontageBuilder(tf, evaluate)
        disjoint_montages = mb.construct_all_montages()

        if not evaluate:
            print('Creating photoshop script ...')
            transformations = [x[0] for x in disjoint_montages]
            if batch:
                name = photoshop_directory.split('/')[-1]
            else:
                name = None
            script_maker.write_photoshop_script(transformations, photoshop_directory, name=name)
        else:
            indices_list = [x[1] for x in disjoint_montages]
            subject = directory.split('/')[-2]
            mb.save_pieces(indices_list, subject)

        
        
if __name__ == '__main__':
    main()