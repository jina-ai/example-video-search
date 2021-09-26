import random
import os
import subprocess
import glob
import shutil
import urllib.request
import string
import io

import numpy as np

from jina import Document, DocumentArray, Executor, requests
from jina.logging.logger import JinaLogger
from jina.types.document import _is_datauri


class FrameExtractor(Executor):
    def __init__(self, max_num_frames: int = 20, **kwargs):
        super().__init__(**kwargs)
        self.max_num_frames = max_num_frames
        self.logger = JinaLogger(getattr(self.metas, 'name', self.__class__.__name__)).logger

    @requests(on='/index')
    def extract(self, docs: DocumentArray, **kwargs):
        for doc in docs:
            self.logger.info(f'received {doc.id}')
            frame_fn_list = self._extract(doc.uri)
            for frame_fn in frame_fn_list:
                self.logger.debug(f'frame: {frame_fn}')
                _chunk = Document(uri=frame_fn)
                _chunk.convert_uri_to_datauri()
                _chunk.convert_image_datauri_to_blob()
                _chunk.blob = np.array(_chunk.blob).astype('uint8')
                _chunk.uri = frame_fn
                doc.chunks.append(_chunk)
            self._delete_tmp(frame_fn_list)

    def _extract(self, uri):
        source_fn = self.save_uri_to_tmp_file(uri) if _is_datauri(uri) else uri
        self.logger.debug(f'extracting {source_fn}')
        _base_fn = os.path.basename(uri).split('.')[0]
        target_path = os.path.join(self.workspace, f'{_base_fn}')
        result = []
        os.makedirs(target_path, exist_ok=True)
        try:
            subprocess.check_call(
                f'ffmpeg -loglevel panic -i {source_fn} -vf fps=.5 -frames 10 -s 960x540 '
                f'{os.path.join(target_path, f"%d.jpg")} >/dev/null 2>&1',
                shell=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f'frame extraction failed, {uri}, {e}')
            return result
        for fn in glob.glob(f'{target_path}/*.jpg'):
            result.append(fn)
        if _is_datauri(uri):
            os.remove(source_fn)
        return result[:self.max_num_frames]

    def save_uri_to_tmp_file(self, uri):
        req = urllib.request.Request(uri, headers={'User-Agent': 'Mozilla/5.0'})
        tmp_fn = os.path.join(
            self.workspace,
            ''.join([random.choice(string.ascii_lowercase) for i in range(10)]) + '.mp4')
        with urllib.request.urlopen(req) as fp:
            buffer = fp.read()
            binary_fn = io.BytesIO(buffer)
            with open(tmp_fn, 'wb') as f:
                f.write(binary_fn.read())
        return tmp_fn

    def _delete_tmp(self, frame_fn_list):
        _path_to_remove = set()
        for fn in frame_fn_list:
            if os.path.exists(fn):
                _path = os.path.dirname(fn)
                _path_to_remove.add(_path)
        for _path in _path_to_remove:
            try:
                shutil.rmtree(_path)
            except OSError as e:
                self.logger.error(f'Error in deleting {_path}: {e}')
