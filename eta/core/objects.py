'''
Core data structures for working with objects in images.

Copyright 2017-2018, Voxel51, LLC
voxel51.com

Brian Moore, brian@voxel51.com
'''
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *
# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import random
import os

from eta.core.geometry import BoundingBox
import eta.core.image as etai
from eta.core.serial import Serializable
import eta.core.utils as etau


class ObjectContainer(Serializable):
    '''Base class for containers that store lists of objects.

    This class should not be instantiated directly. Instead a subclass should
    be created for each type of object to be stored.

    Attributes:
        objects: a list of objects
    '''

    # The class of the objects stored in the container
    _OBJ_CLS = None

    def __init__(self, objects=None):
        '''Constructs an ObjectContainer.

        Args:
            objects: optional list of objects to store.
        '''
        self._validate()
        self.objects = objects or []

    @classmethod
    def get_object_class(cls):
        '''Gets the class of object stored in this container.'''
        return cls._OBJ_CLS

    @property
    def num_objects(self):
        '''The number of objects in the container.'''
        return len(self.objects)

    def add(self, obj):
        '''Adds an object to the container.

        Args:
            obj: an object instance
        '''
        self.objects.append(obj)

    def get_matches(self, filters, match=any):
        '''Returns an object container containing only objects that match the
        filters.

        Args:
            filters: a list of functions that accept objects and return
                True/False
            match: a function (usually `any` or `all`) that accepts an iterable
                and returns True/False. Used to aggregate the outputs of each
                filter to decide whether a match has occurred. The default is
                `any`
        '''
        return self.__class__(
            objects=list(filter(
                lambda o: match(f(o) for f in filters),
                self.objects,
            )),
        )

    def count_matches(self, filters, match=any):
        '''Counts number of objects that match the filters.

        Args:
            filters: a list of functions that accept objects and return
                True/False
            match: a function (usually `any` or `all`) that accepts an iterable
                and returns True/False. Used to aggregate the outputs of each
                filter to decide whether a match has occurred. The default is
                `any`
        '''
        return len(self.get_matches(filters, match=match).objects)

    @classmethod
    def from_dict(cls, d):
        '''Constructs an ObjectContainer from a JSON dictionary.'''
        cls._validate()
        return cls(objects=[cls._OBJ_CLS.from_dict(do) for do in d["objects"]])

    @classmethod
    def _validate(cls):
        if cls._OBJ_CLS is None:
            raise ValueError(
                "_OBJ_CLS is None; note that you cannot instantiate "
                "ObjectContainer directly."
            )


class DetectedObject(Serializable):
    '''A detected object in an image.

    Attributes:
        label: object label
        confidence: detection confidence
        bounding_box: a BoundingBox around the object
    '''

    def __init__(self, label, confidence, bounding_box):
        '''Constructs a DetectedObject.

        Args:
            label: object label string
            confidence: detection confidence, in [0, 1]
            bounding_box: a BoundingBox around the object
        '''
        self.label = str(label)
        self.confidence = float(confidence)
        self.bounding_box = bounding_box

    def extract_from(self, img, force_square=False):
        '''Extracts the subimage containing this object from the image.

        Args:
            img: an image
            force_square: whether to (minimally) manipulate the object bounding
                box during extraction so that the returned subimage is square
        '''
        return self.bounding_box.extract_from(img, force_square=force_square)

    @classmethod
    def from_dict(cls, d):
        '''Constructs a DetectedObject from a JSON dictionary.'''
        return cls(
            d["label"],
            d["confidence"],
            BoundingBox.from_dict(d["bounding_box"]),
        )


class Frame(ObjectContainer):
    '''Container for detected objects in a frame.'''

    _OBJ_CLS = DetectedObject

    def label_set(self):
        '''Returns a set containing the labels of the DetectedObjects.'''
        return set(obj.label for obj in self.objects)


class ObjectCounts(Serializable):
    '''Container for counting objects in an image.'''

    def __init__(self, counts=None):
        '''Constructs an ObjectCounts container.

        Args:
            counts: optional list of ObjectCount objects
        '''
        self.counts = counts or []

    def add(self, count):
        '''Adds an ObjectCount to the container.'''
        self.counts.append(count)

    @classmethod
    def from_dict(cls, d):
        '''Constructs an ObjectCounts from a JSON dictionary.'''
        return ObjectCounts(
            counts=[ObjectCount.from_dict(dc) for dc in d["counts"]]
        )


class ObjectCount(Serializable):
    '''The number of instances of an object found in an image.'''

    def __init__(self, label, count):
        self.label = str(label)
        self.count = int(count)

    @classmethod
    def from_dict(cls, d):
        '''Constructs an ObjectCount from a JSON dictionary.'''
        return ObjectCount(d["label"], d["count"])


class ScoredDetection(Serializable):
    '''A DetectedObject decorated with a source and score.

    Attributes:
        detected_object: a DetectedObject instance
        score: the score of the object
        feat: the feature (embedding) of the object
        source_path: the path to the source image of the detection
        chip_path: the path to the chip image of the detection
    '''

    def __init__(
            self, detected_object, score=0.0, feat=None, source_path=None,
            chip_path=None, chip=None):
        '''Constructs a ScoredDetection.'''
        self.detected_object = detected_object
        self.score = score
        self.feat = feat
        self.source_path = source_path
        self.chip_path = chip_path
        self._chip = chip

    def randomize_score(self):
        '''Sets the score to a random number in [0, 1].'''
        self.score = random.randrange(0.0, 1.0)

    def get_chip(self, img, force_square=False):
        '''Extracts the subimage containing this object from the image.

        Args:
            img: an image
            force_square: whether to (minimally) manipulate the object bounding
                box during extraction so that the returned subimage is square
        '''
        if not img:
            img = etai.read(self.source_path)

        self._chip = self.detected_object.bounding_box.extract_from(
            img, force_square=force_square)
        return self._chip

    @classmethod
    def from_dict(cls, d):
        '''Constructs a DetectedObject from a JSON dictionary.'''
        return cls(
            DetectedObject.from_dict(d["detected_object"]),
            score=d["score"],
            feat=d["feat"],
            source_path=d["source_path"],
            chip_path=d["chip_path"],
        )


class ScoredDetections(ObjectContainer):
    '''Container for scored detections in a frame.'''

    _OBJ_CLS = ScoredDetection

    def __init__(self, objects=None):
        '''Constructs a ScoredDetections instance.

        Args:
            objects: optional list of ScoredDetection instances
        '''
        super(ScoredDetections, self).__init__(objects=objects)
        self._orig_order = None

    def label_set(self):
        '''Returns a set containing the labels of the ScoredDetection objects
        in the container.
        '''
        return set(obj.detected_object.label for obj in self.objects)

    def randomize_scores(self):
        '''Sets all the scores of all objects to random numbers in [0, 1].'''
        for obj in self.objects:
            obj.randomize_score()

    def sort(self):
        '''Sorts the ScoredDetection object list in ascending order by score
        and stores the original order of the objects before the sort.
        '''
        ord_objs = sorted(enumerate(self.objects), key=lambda x: x[1].score)
        self._orig_order, self.objects = zip(*ord_objs)
        return self.objects

    def get_orig_order(self):
        '''Returns an index list defining the order of the objects prior to the
        last sort.
        '''
        return self._orig_order

    def to_html(self, query_img, results_dir, max_objects=25):
        '''Writes the scored detections to HTML for visualization.

        This function writes `query.png` and `index.html` files to the
        `results_dir` directory.

        Args:
            query_img: the query image used to populate the scores
            results_dir: the directory to write the query results to
            max_objects: the maximum number of objects to write. By default, 25
        '''
        etau.ensure_dir(results_dir)

        # Write query image
        etai.write(query_img, os.path.join(results_dir, "query.png"))

        # Generate results HTML
        top_matches_html = ""
        for idx in range(min(len(self.objects), max_objects)):
            obj = self.objects[idx]
            top_matches_html += "<img src=%s height=50>score:%.02f<br>" % (
                os.path.abspath(obj.chip_path), obj.score)

        html_str = """
            <html>
            <body>
            Query:<img src=query.png height=50><hr>Top Matches<hr>""" + \
            top_matches_html + \
            """</body>
            </html>
        """

        # Write results HTML
        with open(os.path.join(results_dir, "index.html"), "wt") as f:
            f.write(html_str)
