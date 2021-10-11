import random
import os
import subprocess
import glob
import shutil
import urllib.request
import string
import io
from typing import Optional
from collections import defaultdict

import numpy as np

from jina import Document, DocumentArray, Executor, requests
from jina.logging.logger import JinaLogger
from jina.types.document import _is_datauri


_ALLOWED_METRICS = ['min', 'max', 'mean_min', 'mean_max']
DEFAULT_FPS = 1


class FrameExtractor(Executor):
    """
    Extract the frames from videos with `ffmpeg`
    """
    def __init__(self, max_num_frames: int = 50, fps=DEFAULT_FPS, debug=False, **kwargs):
        """

        :param max_num_frames:
        :param fps:
        :param debug: If True, the extracted frames are kept in `{workspace}/{video_fn}/*.jpg`
        :param kwargs:
        """
        super().__init__(**kwargs)
        self.max_num_frames = max_num_frames
        self.fps = fps
        self.logger = JinaLogger(getattr(self.metas, 'name', self.__class__.__name__)).logger
        self.debug = debug

    @requests(on='/index')
    def extract(self, docs: DocumentArray, **kwargs):
        """
        Load the video from the Document.uri, extract frames and save the frames into chunks.blob

        :param docs: the input Documents with either the video file name or URL in the `uri` field
        """
        for doc in docs:
            self.logger.info(f'received {doc.id}')
            frame_fn_list = self._extract(doc.uri)
            for frame_fn in frame_fn_list:
                self.logger.debug(f'frame: {frame_fn}')
                _chunk = Document(uri=frame_fn)
                _chunk.convert_uri_to_datauri()
                _chunk.convert_image_datauri_to_blob()
                _chunk.blob = np.array(_chunk.blob).astype('uint8')
                timestamp = self._get_timestamp_from_filename(frame_fn)
                _chunk.location.append(np.uint32(timestamp))
                # _chunk.uri = frame_fn
                doc.chunks.append(_chunk)
            if not self.debug:
                self._delete_tmp(frame_fn_list)

    def _extract(self, uri):
        source_fn = self._save_uri_to_tmp_file(uri) if _is_datauri(uri) else uri
        self.logger.debug(f'extracting {source_fn}')
        _base_fn = os.path.basename(uri).split('.')[0]
        target_path = os.path.join(self.workspace, f'{_base_fn}')
        result = []
        os.makedirs(target_path, exist_ok=True)
        try:
            subprocess.check_call(
                f'ffmpeg -loglevel panic -i {source_fn} -vsync 0 -vf fps={self.fps} -frame_pts true -s 960x540 '
                f'{os.path.join(target_path, f"%d.jpg")} >/dev/null 2>&1',
                shell=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f'frame extraction failed, {uri}, {e}')
        finally:
            for fn in glob.glob(f'{target_path}/*.jpg'):
                result.append(fn)
            if _is_datauri(uri):
                os.remove(source_fn)
            return result[:self.max_num_frames]

    def _save_uri_to_tmp_file(self, uri):
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

    def _get_timestamp_from_filename(self, uri):
        return os.path.basename(uri).split('.')[0]


class SimpleRanker(Executor):
    """
    Aggregate the matches and overwrite document.matches with the aggregated results.
    """
    def __init__(
        self,
        metric: str = 'cosine',
        ranking: str = 'min',
        top_k: int = 10,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if ranking not in _ALLOWED_METRICS:
            raise ValueError(
                f'ranking should be one of {_ALLOWED_METRICS}, got "{ranking}"',
            )

        self.metric = metric
        self.ranking = ranking
        self.top_k = top_k

    @requests(on='/search')
    def merge_matches(self, docs: Optional[Document] = [], paramerters = {}, **kwargs):
        if not docs:
            return
        top_k = int(paramerters.get('top_k', self.top_k))
        for doc in docs:
            parents_matches = defaultdict(list)
            for m in doc.matches:
                parents_matches[m.parent_id].append(m)
            new_matches = []
            for match_parent_id, matches in parents_matches.items():
                best_id = 0
                if self.ranking == 'min':
                    best_id = np.argmin([m.scores[self.metric].value for m in matches])
                elif self.ranking == 'max':
                    best_id = np.argmax([m.scores[self.metric].value for m in matches])
                new_match = matches[best_id]
                new_match.id = matches[best_id].parent_id
                new_match.scores = {self.metric: matches[best_id].scores[self.metric]}
                timestamp = matches[best_id].location[0]
                new_match.tags['timestamp'] = float(timestamp) / DEFAULT_FPS
                vid = new_match.id.split('.')[0]
                new_match.uri = f'https://www.youtube.com/watch?v={vid}'
                new_matches.append(new_match)

            # Sort the matches
            doc.matches = new_matches
            if self.ranking == 'min':
                doc.matches.sort(key=lambda d: d.scores[self.metric].value)
            elif self.ranking == 'max':
                doc.matches.sort(key=lambda d: -d.scores[self.metric].value)
            doc.matches = doc.matches[:top_k]
            doc.pop('embedding')

