from . import transformation_finder
from . import montage_builder
from . import input_pipeline
from . import script_maker

import yaml

import os
from time import time
import sys


def main(directory, nominal, eye, naming, photoshop_directory, q, e):

    print(directory)
    alg_start = time()
    # gets all our files matched with different modalities
    print('Getting all files ...')
    m = input_pipeline.InputPipeline(directory, nominal, naming, eye)
    mmList = m.as_multi_modal_objects()

    # calculates all keypoints and descriptors
    # then constructs a global registration out
    # of pairwise registrations
    for i, fov in enumerate(mmList):
        s = time()
        print('Computing keypoints and descriptors for {} fov...'.format(fov))
        tf = transformation_finder.TransformationFinder(mmList[fov])
        tf.compute_kps_desc()

        print('Building registrations for {} fov...'.format(fov))
        tf.compute_pairwise_registrations(q, i, fov)

        print('Finished {} fov!'.format(fov))
        print('took {}'.format(time() - s))

        # list of lists. The top layer is disjoint
        # montages, followed by the transformations
        # and file names neededd
        mb = montage_builder.MontageBuilder(tf, evaluate=False)
        disjoint_montages = mb.construct_all_montages()

        print('Creating photoshop script ...')
        transformations = [x[0] for x in disjoint_montages]
        name = 'create_recent_montage_' + str(fov) + '_fov'
        script_maker.write_photoshop_script(transformations, photoshop_directory, name=name)
    e.set()
    print('Total time taken {}'.format(time() - alg_start))
    # todo clean up temp
