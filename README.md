# example-video-search
This is an example of search videos using jina

## Prerequisites

```bash
brew install ffmpeg
pip install -r requirements.txt
```

## Usage
Index `/toy-data` and run three sample queries

```bash
python app.py
```

To index other videos, 

```bash
python app.py -d my_data_folder
```

You can also serve the RESTful service after indexing `/toy-data`.

```bash
python app.py -m restful
```

Afterwards, you can query with

```bash
curl -X 'POST' 'localhost:45678/search' \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{"data": [{"text": "this is a highway"}]}'
```

The retrieved results contains the video filename (id) and the best matched frame in that video together with its 
timestamp.

![](.github/matches.png)

After indexing once, you can query without indexing by

```bash
python app.py -m restful_query
```


## How it works
The flow is as below

![](.github/flow.jpg)

When sending requests to `/index`, the video files will be processed as below 
1. The frames are extracted from the videos and saved in the chunks by `frame_extractor`
2. Each frame in the chunks are encoded into vectors by `image_encoder`
3. All the frame are indexed by `indexer`

After indexing, the requests are sent to `/search` with the query text. The query text are processed
1. The text is encoded into vectors by `text_encoder`. Note that `frame_extractor` and `image_encoder` won't process the request.
2. The encoded vectors are used to retrieve the top K nearest neighbors (frames) from the index by `indexer`
3. The retrieved frames are aggregated to find the most related videos by `ranker`. The timestamp of the most related frame in the videos is stored in `Document.tags['timestamp']`
