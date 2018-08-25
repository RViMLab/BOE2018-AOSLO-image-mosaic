from PIL import Image
import numpy as np

def load_from_fname(fname):
    """
        loads image and gets rid of any extra unused dimensions
        as they smeetimes save as rgb accidently
    """
    im = Image.open(fname)
    if len(im.split()) > 1:
        im = im.split()[0]
    im = np.array(im.getdata(), dtype = np.uint8).reshape(im.size[1], im.size[0])
    return im

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '*'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total: 
        print()
