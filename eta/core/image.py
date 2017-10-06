'''
Core image processing tools.

Copyright 2017, Voxel51, LLC
voxel51.com

Brian Moore, brian@voxel51.com
'''
import os
from subprocess import Popen, PIPE

import cv2
import numpy as np

import utils


def read(path, flag=cv2.IMREAD_UNCHANGED):
    '''Reads image from path.'''
    return cv2.imread(path, flag)


def write(img, path):
    '''Writes image to file, creating the output directory if necessary.'''
    utils.ensure_dir(path)
    cv2.imwrite(path, img)


def resize(img, width=None, height=None, *args, **kwargs):
    '''Resizes the given image to the given width and height. At most one
    dimension can be None, in which case the aspect-preserving value is used.
    '''
    if height is None:
        height = int(round(img.shape[0] * (width * 1.0 / img.shape[1])))
    if width is None:
        width = int(round(img.shape[1] * (height * 1.0 / img.shape[0])))
    return cv2.resize(img, (width, height), *args, **kwargs)


def to_double(img):
    '''Converts img to a double precision image with values in [0, 1].'''
    return img.astype(np.float) / np.iinfo(img.dtype).max


def rasterize(vector_path, width):
    '''Renders a vector image as a raster image with the given width,
    in pixels.
    '''
    with utils.TempDir() as d:
        try:
            png_path = os.path.join(d, "tmp.png")
            Convert(
                in_opts=["-density", "1200", "-trim"],
                out_opts=["-resize", str(width)],
            ).run(vector_path, png_path)
            return read(png_path)
        except:
            # Fail gracefully
            return None

    # @todo why is it slightly blurry this way?
    # try:
    #     out = Convert(
    #         in_opts=["-density", "1200", "-trim"],
    #         out_opts=["-resize", str(width)],
    #     ).run(vector_path, "png:-")
    #     return read(out)
    # except:
    #     # Fail gracefully
    #     return None


def overlay(im1, im2, x0=0, y0=0):
    '''Overlays im2 onto im1 at the specified coordinates.

    Args:
        im1: a numpy array of any type containing a non-transparent image
        im2: a numpy array of any type containing a possibly-transparent image
        (x0, y0): the top-left coordinate of im2 in im1 after overlaying, where
            (0, 0) corresponds to the top-left of im1. This coordinate may lie
            outside of im1, in which case some (even all) of im2 may be omitted

    Returns:
        a uint8 numpy array containing the final image
    '''
    im1 = to_double(im1)
    im2 = to_double(im2)
    h1, w1 = im1.shape[:2]
    h2, w2 = im2.shape[:2]

    # Active slice of im1
    y1t = np.clip(y0, 0, h1)
    y1b = np.clip(y0 + h2, 0, h1)
    x1l = np.clip(x0, 0, w1)
    x1r = np.clip(x0 + w2, 0, w1)
    y1 = slice(y1t, y1b)
    x1 = slice(x1l, x1r)

    # Active slice of im2
    y2t = np.clip(y1t - y0, 0, h2)
    y2b = y2t + y1b - y1t
    x2l = np.clip(x1l - x0, 0, w2)
    x2r = x2l + x1r - x1l
    y2 = slice(y2t, y2b)
    x2 = slice(x2l, x2r)

    if im2.shape[2] == 4:
        # Mix transparent image
        alpha = im2[y2, x2, 3][:, :, np.newaxis]
        im1[y1, x1, :] *= (1 - alpha)
        im1[y1, x1, :] += alpha * im2[y2, x2, :3]
    else:
        # Insert opaque image
        im1[y1, x1, :] = im2[y2, x2, :]

    return np.uint8(255 * im1)


def to_frame_size(frame_size=None, shape=None, img=None):
    '''Converts an image size representation to a (width, height) tuple.

    Pass *one* keyword argument to compute the frame size.

    Args:
        frame_size: the (width, height) of the image
        shape: the (height, width, ...) of the image, e.g. from img.shape
        img: the image itself

    Returns:
        (w, h): the width and height of the image

    Raises:
        TypeError: if none of the keyword arguments were passed
    '''
    if img is not None:
        shape = img.shape
    if shape is not None:
        return shape[1], shape[0]
    elif frame_size is not None:
        return frame_size
    else:
        raise TypeError("A valid keyword argument must be provided")


class Convert(object):
    '''Interface for the ImageMagick convert binary.'''

    def __init__(
            self,
            executable="convert",
            in_opts=None,
            out_opts=None,
        ):
        '''Constructs a convert command, minus the input/output paths.

        Args:
            executable: the system path to the convert binary
            in_opts: a list of input options for convert
            out_opts: a list of output options for convert
        '''
        self._executable = executable
        self._in_opts = in_opts or []
        self._out_opts = out_opts or []
        self._args = None
        self._p = None

    @property
    def cmd(self):
        '''The last executed convert command string, or None if run() has not
        yet been called.
        '''
        return " ".join(self._args) if self._args else None

    def run(self, inpath, outpath):
        '''Run the convert binary with the specified input/outpath paths.

        Args:
            inpath: the input path
            outpath: the output path. Use "-" or a format like "png:-" to pipe
                output to STDOUT

        Returns:
            out: STDOUT of the convert binary

        Raises:
            ExecutableNotFoundError: if the convert binary cannot be found
            ExecutableRuntimeError: if the convert binary raises an error during
                execution
        '''
        self._args = (
            [self._executable] +
            self._in_opts + [inpath] +
            self._out_opts + [outpath]
        )

        try:
            self._p = Popen(self._args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise utils.ExecutableNotFoundError(self._executable)
            else:
                raise

        out, err = self._p.communicate()
        if self._p.returncode != 0:
            raise utils.ExecutableRuntimeError(self.cmd, err)

        return out


class Length(object):
    '''Represents a length along a specified dimension of an image as a relative
    percentage or an absolute pixel count.
    '''

    def __init__(self, length_str, dim):
        '''Builds a Length object.

        Args:
            length_str: a string of the form '<float>%' or '<int>px' describing
                a relative or absolute length, respectively
            dim: the dimension to measure length along
        '''
        self.dim = dim
        if length_str.endswith("%"):
            self.relunits = True
            self.rellength = 0.01 * float(length_str[:-1])
            self.length = None
        elif length_str.endswith("px"):
            self.relunits = False
            self.rellength = None
            self.length = int(length_str[:-2])
        else:
            raise TypeError(
                "Expected '<float>%%' or '<int>px', received '%s'" %
                    str(length_str))

    def render(self, frame_size=None, shape=None, img=None):
        '''Returns the length in pixels for the given frame size/shape/img.

        Pass any *one* of the keyword arguments to render the length.

        Args:
            frame_size: the (width, height) of the image
            shape: the (height, width, ...) of the image, e.g. from img.shape
            img: the image itself

        Raises:
            LengthError: if none of the keyword arguments were passed
        '''
        if img is not None:
            shape = img.shape
        elif frame_size is not None:
            shape = frame_size[::-1]
        elif shape is None:
            raise LengthError("One keyword argument must be provided")

        if self.relunits:
            return int(round(self.rellength * shape[self.dim]))
        else:
            return self.length


class LengthError(Exception):
    pass


class Width(Length):
    '''Represents the width of an image as a relative percentage or an absolute
    pixel count.
    '''

    def __init__(self, width_str):
        '''Builds a Width object.

        Args:
            width_str: a string of the form '<float>%' or '<int>px' describing
                a relative or absolute width, respectively
        '''
        super(Width, self).__init__(width_str, 1)


class Height(Length):
    '''Represents the height of an image as a relative percentage or an absolute
    pixel count.
    '''

    def __init__(self, height_str):
        '''Builds a Height object.

        Args:
            height_str: a string of the form '<float>%' or '<int>px' describing
                a relative or absolute height, respectively
        '''
        super(Height, self).__init__(height_str, 0)


class Location(object):
    '''Represents a location in an image.'''

    # Valid loc strings
    TOP_LEFT  = ["top-left", "tl"]
    TOP_RIGHT = ["top-right", "tr"]
    BOTTOM_RIGHT = ["bottom-right", "br"]
    BOTTOM_LEFT  = ["bottom-left", "bl"]

    def __init__(self, loc):
        '''Constructs a Location object.

        Args:
            loc: a (case-insenstive) string specifying a location
                ["top-left", "top-right", "bottom-right", "bottom-left"]
                ["tl", "tr", "br", "bl"]
        '''
        self._loc = loc.lower()

    @property
    def is_top_left(self):
        '''True if the location is top left, otherwise False.'''
        return self._loc in self.TOP_LEFT

    @property
    def is_top_right(self):
        '''True if the location is top right, otherwise False.'''
        return self._loc in self.TOP_RIGHT

    @property
    def is_bottom_right(self):
        '''True if the location is bottom right, otherwise False.'''
        return self._loc in self.BOTTOM_RIGHT

    @property
    def is_bottom_left(self):
        '''True if the location is bottom left, otherwise False.'''
        return self._loc in self.BOTTOM_LEFT


def hex_to_rgb(value):
    '''Converts "#rrbbgg" to a (red, green, blue) tuple.'''
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_bgr(value):
    '''Converts "#rrbbgg" to a (blue, green, red) tuple.'''
    return hex_to_rgb(value)[::-1]


def rgb_to_hex(red, green, blue):
    '''Converts (red, green, blue) to a "#rrbbgg" string.'''
    return "#%02x%02x%02x" % (red, green, blue)


def bgr_to_hex(blue, green, red):
    '''Converts (blue, green, red) to a "#rrbbgg" string.'''
    return rgb_to_hex(red, green, blue)


def rgb_to_bgr(img):
    '''Converts an RGB image to a BGR image.'''
    return img[..., [2, 1, 0] + range(3, img.shape[2])]


def bgr_to_rgb(img):
    '''Converts a BGR image to an RGB image.'''
    return rgb_to_bgr(img)  # this operation is symmetric
