import glob
import os
import click

from jina import Document, DocumentArray, Flow


def config():
    os.environ['JINA_PORT'] = '45678'
    os.environ['JINA_WORKSPACE'] = './workspace'


def get_docs(data_path):
    for fn in glob.glob(os.path.join(data_path, '*.mp4')):
        yield Document(uri=fn)


@click.command()
@click.option('--mode', '-m', type=click.Choice(['restful', 'grpc']), default='grpc')
def main(mode):
    config()
    workspace = os.environ["JINA_WORKSPACE"]
    if mode == 'grpc':
        f = Flow.load_config(
            'flow.yml',
            override_with={
                'protocol': 'grpc',
                'cors': False})
    with f:
        if os.path.exists(workspace):
            print(
                f'\n +------------------------------------------------------------------------------------+ \
                  \n |                                   🤖🤖🤖                                           | \
                  \n | The directory {workspace} already exists. Please remove it before indexing again. | \
                  \n |                                   🤖🤖🤖                                           | \
                  \n +------------------------------------------------------------------------------------+'
            )
            return -1
        resp = f.post(
            on='/index',
            inputs=get_docs('toy-data'),
            request_size=2,
            return_results=True)
        print(f'resp: {resp}')
        f.post(
            on='/search',
            inputs=get_docs('toy-data'),
            request_size=2,
            return_results=True)

