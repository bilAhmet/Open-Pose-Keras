
import h5py
from py_rmpe_config import RmpeGlobalConfig, RmpeCocoConfig
import random
from py_rmpe_transformer import Transformer, AugmentSelection
from py_rmpe_heatmapper import Heatmapper
import json
import numpy as np

class DataIterator:

    def __init__(self, h5file, shuffle = True, augment = True):

        self.h5file = h5file
        self.h5 = h5py.File(self.h5file, "r")
        self.datum = self.h5['datum']
        self.heatmapper = Heatmapper()
        self.augment = augment
        self.shuffle = shuffle

    def iterate(self):

        keys = list(self.datum.keys())

        if self.shuffle:
            random.shuffle(keys)

        for key in keys:

            image, mask, meta = self.read_data(key)
            debug = {}

            print("[in] IMAGE:", image.shape, image.dtype, meta['img_path'])
            print("[in] MASK:", mask.shape, mask.dtype, meta['mask_miss_path'])

            debug['img_path']=meta['img_path']
            debug['mask_miss_path'] = meta['mask_miss_path']
            debug['mask_all_path'] = meta['mask_all_path']

            image, mask, meta, labels = self.transform_data(image, mask, meta)
            image = np.transpose(image, (2, 0, 1))

            yield image, mask, labels, debug

    def num_keys(self):
        return len(list(self.datum.keys()))

    def read_data(self, key):

        entry = self.datum[key]

        assert 'meta' in entry.attrs, "No 'meta' attribute in .h5 file. Did you generate .h5 with new code?"

        meta = json.loads(entry.attrs['meta'])
        meta['joints'] = RmpeCocoConfig.convert(np.array(meta['joints']))
        data = entry.value

        if data.shape[0] <= 6:
            # TODO: this is extra work, should write in store in correct format (not transposed)
            # can't do now because I want storage compatibility yet
            # we need image in classical not transposed format in this program for warp affine
            data = data.transpose([1,2,0])

        img = data[:,:,0:3]
        mask_miss = data[:,:,4]
        mask = data[:,:,5]

        return img, mask_miss, meta

    def transform_data(self, img, mask,  meta):

        aug = AugmentSelection.random() if self.augment else AugmentSelection.unrandom()
        img, mask, meta = Transformer.transform(img, mask, meta, aug=aug)
        labels = self.heatmapper.create_heatmaps(meta['joints'], mask)

        return img, mask, meta, labels


    def __del__(self):

        self.h5.close()
