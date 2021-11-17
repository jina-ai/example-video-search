# Build A Video Search System using Jina

**NOTE**: The simplified version of this example is at [feat-simple-tutorial](https://github.com/jina-ai/example-video-search/tree/feat-simple-tutorial) branch, which contains the full codes for the tutorial at [docs.jina.ai](https://docs.jina.ai/tutorials/video-search)

Imagine that you remember one specific scene from a movie, for example the scene from
The Lord of the Rings where Gandalf is figthing the dragon Balrog. Unfortunately, you forgot both
the name Gandalf and Balrog and also in which of the three movies the scene occurred. How could you find the correct scene in the movie now?
This is where this example can help you. This Video Search System allows you to search in movies based on text. 
This means you could search 'Old wizard fighting dragon' and the search system would return the correct movie and timestamp of the scene.

**Table of Contents**
- [Build A Video Search System using Jina](#build-a-video-search-system-using-jina)
  - [Overview](#overview)
  - [🐍 Build the app with Python](#-build-the-app-with-python)
    - [🗝️ Requirements](#️-requirements)
    - [👾 Step 1. Clone the repo and install Jina](#-step-1-clone-the-repo-and-install-jina)
    - [Step 2. Download the AudioCLIP model.](#step-2-download-the-audioclip-model)
    - [🏃 Step 3. Index your data](#-step-3-index-your-data)
    - [🔎 Step 4: Query your data](#-step-4-query-your-data)
  - [🌀 Flow diagram](#-flow-diagram)
    - [Indexing](#indexing)
    - [Querying](#querying)
  - [🔮 Overview of the files](#-overview-of-the-files)
  - [⏭️ Next steps](#️-next-steps)
  - [👩‍👩‍👧‍👦 Community](#-community)
  - [🦄 License](#-license)


## Overview
| About this example: |  |
| ------------- | ------------- |
| Learnings | How to search through both image frames and audio of a video. |
| Used for indexing | Video Files. |
| Used for querying | Text Query (e.g. "girl studying engineering") |
| Dataset used | Choose your own videos |
| Model used | [AudioCLIP](https://github.com/AndreyGuzhov/AudioCLIP) |

In this example, we create a video search system that retrieves the videos based on short text descriptions of the scenes. The main challenge is to enable the user to search videos _**without**_ using any labels or text information about the videos.


We choose to use Audio CLIP models to encode the video frames and audios 

Jina searches both the image frames and the audio of the video and returns
the matched video and a timestamp.

_____

## 🐍 Build the app with Python

These instructions explain how to build the example yourself and deploy it with Python.


### 🗝️ Requirements

1. You have a working Python 3.7 or 3.8 environment and a installation of [Docker](https://docs.docker.com/get-docker/). Ensure that you set enough memory resources(more than 6GB) to docker. You can set it in settings/resources/advanced in Docker.
2. We recommend creating a [new Python virtual environment](https://docs.python.org/3/tutorial/venv.html) to have a clean installation of Jina and prevent dependency conflicts.   
3. You have at least 5 GB of free space on your hard drive. 

### 👾 Step 1. Clone the repo and install Jina

Begin by cloning the repo, so you can get the required files and datasets.

```sh
git clone https://github.com/jina-ai/example-video-search
cd example-video-search
````
In your terminal, you should now be located in the *example-video-search* folder. Let's install Jina and the other required Python libraries. For further information on installing Jina check out [our documentation](https://docs.jina.ai/chapters/core/setup/).

```sh
pip install -r requirements.txt
```

### Step 2. Download the AudioCLIP model.
We recommend you to download the AudioCLIP model in advance.
To do that, run:
```bash
bash scripts/download_model.sh
```

### 🏃 Step 3. Index your data
To quickly get started, you can index a [small dataset](toy-data) to make sure everything is working correctly. 

To index the toy dataset, run
```bash
python app.py -m grpc
```
After indexing, the search flow is started automatically and three simple test queries are performed.
The results are displayed in your terminal.

We recommend you come back to this step later and index more data.

### 🔎 Step 4: Query your data
After indexing once, you can query without indexing by running

```bash
python app.py -m restful_query
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


![](.github/demo.gif)


You can also add more parameters to the query:
```sh
curl -X POST -d '{"parameters":{"top_k": 5}, "data": ["a black dog and a spotted dog are fighting"]}' -H 'accept: application/json' -H 'Content-Type: application/json' 'http://localhost:45678/search'
```

Once you run this command, you should see a JSON output returned to you. This contains the video uri and the timestamp, which together determine one part of the video that matches the query text description.
By default, the `toy_data` contains two videos clipped from YouTube.


## 🌀 Flow diagram
This diagram provides a visual representation of the Flows in this example; Showing which executors are used in which order.
Remember, our goal is to compare vectors representing the semantics of images and audio with vectors encoding the semantics of short text descriptions.

### Indexing
![](.github/index-flow.png)  
As you can see, the Flow that Indexes the data contains two parallel branches: 
- Image: Encodes image frames from the video and indexes them.
- Audio: Encodes audio of the images and indexes it.

### Querying
![](.github/query-flow.png)  
The query flow is different to the index flow. We are encoding the text input using the AudioCLIP model and then
compare the embeddings with the audio and image embeddings we have stored in the indexers.
Then, the indexers add the closest matches to the documents.

## 🔮 Overview of the files

|                      |                                                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 📃 `index-flow.yml`  | YAML file to configure indexing Flow |
| 📃 `search-flow.yml` | YAML file to configure querying Flow |
| 📃 `executors.py`    | File that contains Ranker and ModalityFilter executors  |
| 📂 `workspace/`      | Folder to store indexed files (embeddings and documents). Automatically created after the first indexing   |
| 📂 `toy-data/`       | Folder to store the toy dataset for the example  |
| 📃 `app.py`          | Main file that runs the example  |


## ⏭️ Next steps

Did you like this example and are you interested in building your own? For a detailed tutorial on how to build your Jina app check out [How to Build Your First Jina App](https://docs.jina.ai/chapters/my_first_jina_app/#how-to-build-your-first-jina-app) guide in our documentation.  

To learn more about Jina concepts, check out the [cookbooks](https://github.com/jina-ai/jina/tree/master/.github/2.0/cookbooks).  

If you have any issues following this guide, you can always get support from our [Slack community](https://slack.jina.ai) .

## 👩‍👩‍👧‍👦 Community

- [Slack channel](https://slack.jina.ai) - a communication platform for developers to discuss Jina.
- [LinkedIn](https://www.linkedin.com/company/jinaai/) - get to know Jina AI as a company and find job opportunities.
- [![Twitter Follow](https://img.shields.io/twitter/follow/JinaAI_?label=Follow%20%40JinaAI_&style=social)](https://twitter.com/JinaAI_) - follow us and interact with us using hashtag `#JinaSearch`.  
- [Company](https://jina.ai) - know more about our company, we are fully committed to open-source!

## 🦄 License

Copyright (c) 2021 Jina AI Limited. All rights reserved.

Jina is licensed under the Apache License, Version 2.0. See [LICENSE](https://github.com/jina-ai/jina/blob/master/LICENSE) for the full license text.
