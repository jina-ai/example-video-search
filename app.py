import glob
import shutil

import os
import click

from jina import Document, DocumentArray, Flow
from jina.types.request import Request


def config():
    os.environ['JINA_PORT'] = '45678'  # the port for accessing the RESTful service, i.e. http://localhost:45678/docs
    os.environ['JINA_WORKSPACE'] = './workspace'  # the directory to store the indexed data
    os.environ['TOP_K'] = '50'  # the maximal number of results to return


def get_docs(data_path):
    for fn in glob.glob(os.path.join(data_path, '*.mp4')):
        yield Document(uri=fn, id=os.path.basename(fn))


def check_search(resp: Request):
    for doc in resp.docs:
        print(f'Query text: {doc.text}')
        print(f'Matches:')
        for m in doc.matches:
            print(f'+- id: {m.id}, score: {m.scores["cosine"].value}, timestampe: {m.tags["timestamp"]}')
        print('-'*10)


@click.command()
@click.option('--mode', '-m', type=click.Choice(['restful', 'grpc', 'restful_query']), default='grpc')
@click.option('--directory', '-d', type=click.Path(exists=True), default='toy_data')
def main(mode, directory):
    config()
    workspace = os.environ["JINA_WORKSPACE"]
    if os.path.exists(workspace) and mode != 'restful_query':
        print(
            f'\n +-----------------------------------------------------------------------------------+ \
              \n |                                   🤖🤖🤖                                          | \
              \n | The directory {workspace} already exists. Removing...                             | \
              \n |                                   🤖🤖🤖                                          | \
              \n +-----------------------------------------------------------------------------------+'
        )
        shutil.rmtree(workspace)
    if mode == 'grpc':
        f = Flow.load_config(
            'flow.yml',
            override_with={
                'protocol': 'grpc',
                'cors': False})
    elif mode == 'restful':
        f = Flow.load_config('flow.yml')
    else:
        return -1

    with f:
        if mode != 'restful_query':
            f.post(
                on='/index',
                inputs=get_docs(directory))
            f.post(
                on='/sync',
                parameters={
                    'only_delta': True, 'startup': True
                }
            )
        if mode == 'grpc':
            f.post(
                on='/search',
                inputs=DocumentArray([
                    Document(text='a senior man is reading'),
                    Document(text='a dog and a girl'),
                    Document(text='a baby is walking with the help from its parents'),
                ]),
                on_done=check_search,
                parameters={'traversal_paths': ['r']}
            )
        elif mode in ['restful', 'restful_query']:
            f.block()


if __name__ == '__main__':
    main()
