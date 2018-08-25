import cv2
import numpy as np


def compute_kps_desc(image):
    orb = cv2.ORB_create(
        nfeatures=5000,
    )
    kp, des = orb.detectAndCompute(image, None)
    return kp, des

def match_desc(desc1, desc2, key):
    """return the matches which pass the ratio test"""

    # sometimes there are noe descriptors
    if desc1 is None or desc2 is None:
        return [], key

    FLANN_INDEX_LSH = 6
    index_params = dict(algorithm=FLANN_INDEX_LSH,
                        table_number=6,  # 12
                        key_size=12,  # 20
                        multi_probe_level=1)  # 2
    search_params = dict()  # or pass empty dictionary

    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(desc1, desc2, k=2)

    good_matches = []

    for best_two in matches:
        if len(best_two) > 1:
            m, n = best_two
            if m.distance < 0.9 * n.distance:
                good_matches.append(m)

    return good_matches, key


def ransac(src, dst, iterations=1000, threshold=10.0):
    """ransac written in python as nothing in opencv for just translations"""
    iterations = iterations if iterations < src.shape[0] else src.shape[0]

    # potential transformations given by some row
    rows = np.arange(src.shape[0])
    np.random.shuffle(rows)
    rows = rows[:iterations]

    # all potential translations
    translations = dst[rows, :] - src[rows, :]

    # src = matched_points x dimensions
    # after_tile = num_translations x matched x dimensions
    # translations = num_translations x dimension
    # y = np.tile(src, (iterations, 1, 1)) + translations[:, None, :]
    y = src[None, :, :] + translations[:, None, :]

    # y = trans x matched x dim
    error = (y - dst[None, :, :])
    error *= error
    l2 = np.sum(error, axis=2)

    num_inliers = np.sum(l2 < threshold, axis=1)
    best = np.argmax(num_inliers)

    return num_inliers[best], translations[best]
