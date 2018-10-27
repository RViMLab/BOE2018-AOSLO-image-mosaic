from . import multi_modal_image
from . import features
from . import utils

from scipy import ndimage
import numpy as np
import math
from time import time


class TransformationFinder:

    UNMATCHED = -1
    nom_thresh = 7.
    auto_accept = 50
    avg = 0.
    n = 0.
    """
        Take list of MultiModalImage objects. Compute all the keypoints
        and descriptors. Then try to match these images, thus constructing
        pairwise registrations.
    """
    def __init__(self, mmList):
        self.mmList = mmList
        self._num = len(mmList)

        # a dictionary of 
        # dict[image_id] = sorted_list_of_closest_images
        self.closest_mm_images = self.build_closest()

        # space to store translations, numbers of matches and if we have
        # already calculated some registration
        self.translations = np.zeros([self._num,self._num,2])
        self.inlier_matches = np.zeros([self._num,self._num], dtype=np.int16)
        self.have_computed = np.zeros([self._num,self._num], dtype=np.bool)
        self.min_inliers = 10
        self.matched = None
    
    def build_closest(self,):
        """
            find images closest to each image, below a threshold distance.
            Save this as a sorted list, with the closest first.
            
            output:
                dict[image_id] = sorted_list_of_images
        """

        closest_to = dict()

        # for each image_id
        for src in range(self._num):

            # current image and its location
            src_im = self.mmList[src]
            src_pos = src_im.get_nominal()

            # save all the close enough images here
            dsts = []
            for dst in range(self._num):

                # ignore if same image
                if dst == src:
                    continue

                # distance between src and dst
                dst_im = self.mmList[dst]
                dst_pos = dst_im.get_nominal()
                distance = (src_pos - dst_pos)
                distance = (distance*distance).sum()

                # save if within threshold
                if distance < TransformationFinder.nom_thresh:
                    dsts.append((dst, distance))

            # for current image sort the closest images 
            # based on distance
            dsts.sort(key=lambda x: x[1])
            dsts = list(map(lambda x: x[0], dsts))
            closest_to[src] = dsts
        return closest_to

    def compute_kps_desc(self,):
        for mm in self.mmList:
            mm.calculate_orb()
        
    def match_two_images(self, mm1, mm2):
        """given two MMImages match the descriptors for each channel individually"""
        matches = dict(split=[], confocal=[], avg=[])
        for key in multi_modal_image.MultiModalImage.index.keys():
            modality_matches, key = features.match_desc(mm1.descriptors[key], mm2.descriptors[key], key)
            matches[key] += modality_matches
        return matches

    def get_all_matches(self, i, j):
        """
            combines all matches for each channel into two 
            keypoint point clouds, rather than 6
        """
        mm1 = self.mmList[i]
        mm2 = self.mmList[j]
        matches = self.match_two_images(mm1, mm2)

        srcpts = []
        dstpts = []
        for key in multi_modal_image.MultiModalImage.index.keys():
            kp1 = mm1.keypoints[key]
            kp2 = mm2.keypoints[key]
            ms = matches[key]
            src_pts = np.float32([ kp1[m.queryIdx].pt for m in ms ]).reshape(-1,2)
            dst_pts = np.float32([ kp2[m.trainIdx].pt for m in ms ]).reshape(-1,2)
            srcpts.append(src_pts)
            dstpts.append(dst_pts)

        src_pts = np.concatenate(srcpts, axis=0)
        dst_pts = np.concatenate(dstpts, axis=0)

        return src_pts, dst_pts

    def compute_translation(self, i, j):
        src, dst = self.get_all_matches(i, j)
        inliers, translation = features.ransac(src, dst)

        self.translations[i,j,:] = translation
        self.inlier_matches[i,j] = inliers
        self.have_computed[i,j] = True

    def get_translation(self, i, j):
        return self.translations[i,j,:]

    def get_inliers(self, i, j):
        return self.inlier_matches[i,j]

    def compute_pairwise_registrations(self, q, i, fov):
        matched = np.ones([self._num, 1], dtype=np.int32)*TransformationFinder.UNMATCHED

        # while anything is still unmatched
        total_matched = 0
        while np.any(matched==TransformationFinder.UNMATCHED):
        
            # first unmatched image
            # match to self, ie new global ref
            id_unmatched = np.argmin(matched)
            matched[id_unmatched] = id_unmatched

            # if add new ref check again
            new_ref = True

            while new_ref:

                # make sure something is added
                new_ref = False

                # search through images we will move
                for src_mm in range(self._num):

                    # print progress
                    num_matched = np.sum(matched!=TransformationFinder.UNMATCHED)
                    if num_matched > total_matched:
                        total_matched = num_matched
                        q.put((num_matched, self._num, i, fov))
                        #utils.printProgressBar(total_matched, self._num)

                    # if this is already matched skip
                    if matched[src_mm] != TransformationFinder.UNMATCHED:
                        continue

                    most_inliers = 0
                    best_dst_id = -1

                    # search through possible destination images
                    for dst_mm in self.closest_mm_images[src_mm]:

                        # if images are same, or the dstination hasnt been matched
                        if (dst_mm==src_mm) or (matched[dst_mm]==TransformationFinder.UNMATCHED):
                            continue
                        
                        # if we havent calculated everything already
                        if not self.have_computed[src_mm, dst_mm]:
                            self.compute_translation(src_mm, dst_mm)

                        # if better than all previous
                        if self.inlier_matches[src_mm, dst_mm] >= most_inliers:
                            most_inliers = self.inlier_matches[src_mm, dst_mm]
                            best_dst_id = dst_mm

                            if most_inliers >= TransformationFinder.auto_accept:
                                break

                    if most_inliers > self.min_inliers:
                        matched[src_mm] = best_dst_id
                        new_ref = True
        self.matched = matched