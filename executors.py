from typing import Optional, Iterable
from collections import defaultdict

import numpy as np

from jina import Document, DocumentArray, Executor, requests


_ALLOWED_METRICS = ['min', 'max', 'mean_min', 'mean_max']
DEFAULT_FPS = 1


class FilterModality(Executor):
    def __init__(self,
                 modality: str = None,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.modality = modality

    @requests
    def filter(self, docs: DocumentArray, **kwargs):
        for doc in docs:
            chunks = filter(lambda d: d.modality == self.modality, doc.chunks)
            doc.chunks = chunks
        return docs


class AudioSegmenter(Executor):
    def __init__(self, chunk_duration: int = 10, chunk_strip: int = 1,
                 traversal_paths: Iterable[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_duration = chunk_duration  # seconds
        self.strip = chunk_strip
        self.traversal_paths = traversal_paths

    @requests(on=['/search', '/index'])
    def segment(self, docs: Optional[DocumentArray] = None,
                parameters: dict = None, **kwargs):
        if not docs:
            return
        traversal_paths = parameters.get('traversal_paths', self.traversal_paths)
        for idx, doc in enumerate(docs.traverse_flat(traversal_paths)):
            sample_rate = doc.tags['sample_rate']
            chunk_size = int(self.chunk_duration * sample_rate)
            strip = parameters.get('chunk_strip', self.strip)
            strip_size = int(strip * sample_rate)
            num_chunks = max(1, int((doc.blob.shape[0] - chunk_size) / strip_size))
            chunk_array = DocumentArray()
            for chunk_id in range(num_chunks):
                beg = chunk_id * strip_size
                end = beg + chunk_size
                if beg > doc.blob.shape[0]:
                    break
                chunk_array.append(
                    Document(
                        blob=doc.blob[beg:end],
                        offset=idx,
                        location=[beg, end],
                        tags=doc.tags,
                        modality='audio'
                    )
                )
                ts = (beg / sample_rate) if sample_rate != 0 else 0
                chunk_array[chunk_id].tags['timestamp'] = ts
                chunk_array[chunk_id].tags['video'] = doc.id
            docs[idx].chunks = chunk_array


class MixRanker(Executor):
    """
    Aggregate the matches and overwrite document.matches with the aggregated results.
    """
    def __init__(
        self,
        metric: str = 'cosine',
        ranking: str = 'min',
        top_k: int = 10,
        modality_list: Iterable[str] = ('image', 'audio'),
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
        self.modality_list = modality_list

    @requests(on='/search')
    def merge_matches(self, docs: DocumentArray, parameters=None, **kwargs):
        if not docs:
            return
        top_k = int(parameters.get('top_k', self.top_k))
        for doc in docs:
            parents_matches = defaultdict(list)
            for m in doc.matches:
                if m.modality in self.modality_list:
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
                timestamp = matches[best_id].tags['timestamp']
                if new_match.modality == 'image':
                    new_match.tags['timestamp'] = float(timestamp) / DEFAULT_FPS
                vid = new_match.id.split('.')[0]
                # reconstruct the YouTube URL based on the vid
                new_match.uri = f'https://www.youtube.com/watch?v={vid}#t={int(timestamp)}s'
                new_matches.append(new_match)

            # Sort the matches
            doc.matches = new_matches
            if self.ranking == 'min':
                doc.matches.sort(key=lambda d: d.scores[self.metric].value)
            elif self.ranking == 'max':
                doc.matches.sort(key=lambda d: -d.scores[self.metric].value)
            doc.matches = doc.matches[:top_k]
            doc.pop('embedding')

