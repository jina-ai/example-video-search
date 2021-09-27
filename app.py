import glob
import os
import click

from jina import Document, DocumentArray, Flow
from jina.types.request import Request


def config():
    os.environ['JINA_PORT'] = '45678'
    os.environ['JINA_WORKSPACE'] = './workspace'
    os.environ['TOP_K'] = '50'

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
@click.option('--mode', '-m', type=click.Choice(['restful', 'grpc']), default='grpc')
@click.option('--directory', '-d', type=click.Path(exists=True), default='toy_data')
def main(mode, directory):
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
    elif mode == 'restful':
        f = Flow.load_config('flow.yml')
    with f:
        f.post(
            on='/index',
            inputs=get_docs(directory))
        if mode == 'grpc':
            f.post(
                on='/search',
                inputs=DocumentArray([
                    Document(text='mountain and road'),
                    Document(text='This is a world map'),
                    Document(text='There are many flags of different countries'),
                ]),
                on_done=check_search)
        elif mode == 'restful':
            f.block()


if __name__ == '__main__':
    main()