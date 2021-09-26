import glob
import os
import click

from jina import Document, DocumentArray, Flow
from jina.types.request import Request


def config():
    os.environ['JINA_PORT'] = '45678'
    os.environ['JINA_WORKSPACE'] = './workspace'


def get_docs(data_path):
    for fn in glob.glob(os.path.join(data_path, '*.mp4')):
        yield Document(uri=fn)


def check_index(resp: Request):
    for doc in resp.docs:
        print(f'{doc.uri}')
        for c in doc.chunks:
            print(f'+- {c.uri}, {c.embedding.shape}')


def check_search(resp: Request):
    for doc in resp.docs:
        print(f'{doc.uri}')
        for m in doc.matches:
            print(f'+- {m.uri}, {m.scores["cosine"].value}')


@click.command()
@click.option('--mode', '-m', type=click.Choice(['restful', 'grpc']), default='grpc')
def main(mode):
    config()
    workspace = os.environ["JINA_WORKSPACE"]
    if os.path.exists(workspace):
        print(
            f'\n +-----------------------------------------------------------------------------------+ \
              \n |                                   🤖🤖🤖                                           | \
              \n | The directory {workspace} already exists. Please remove it before indexing again. | \
              \n |                                   🤖🤖🤖                                           | \
              \n +-----------------------------------------------------------------------------------+'
        )
        return -1
    if mode == 'grpc':
        f = Flow.load_config(
            'flow.yml',
            override_with={
                'protocol': 'grpc',
                'cors': False})
    with f:
        f.post(
            on='/index',
            inputs=get_docs('toy_data'),
            on_done=check_index)

        f.post(
            on='/search',
            inputs=DocumentArray([Document(text='hello')]),
            on_done=check_search)

if __name__ == '__main__':
    main()