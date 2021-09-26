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


## How it works
When sending requests to `/index`, the video files in the will be processed as below 
1. The frames are extracted from the videos and saved in the chunks
2. Each frame in the chunks are encoded into vectors by `CLIPImageEncoder`
3. All the frame are indexed by `SimpleIndexer`

After indexing, the search requests are sent to `/search` with the query in text. The query text are processed
1. The text is encoded into vectors by `CLIPTextEncoder`
2. The encoded vectors are used to retrieve the top K nearest neighbors (frames) from the index
3. The retrieved frames are aggregated to find the most related videos. The timestamp of the most related frame in the videos is stored in `Document.tags['timestamp']`
