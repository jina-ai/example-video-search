import glob
import os
import click

from jina import Document, DocumentArray, Flow
from jina.types.request import Request


def config():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(cur_dir, "models")
    workspace_dir = os.path.join(cur_dir, "workspace")
    os.environ['JINA_PORT'] = '45678'  # the port for accessing the RESTful service, i.e. http://localhost:45678/docs
    os.environ['JINA_WORKSPACE'] = './workspace'  # the directory to store the indexed data
    os.environ['TOP_K'] = '50'  # the maximal number of results to return
    os.environ['MODEL_MOUNT_ASSETS'] = f'{model_dir}:/workdir/assets'
    os.environ['MODEL_MOUNT_CACHE'] = f'{model_dir}:/workdir/.cache'
    os.environ['WORKSPACE_MOUNT'] = f'{workspace_dir}:/workdir/workspace'


def get_docs(data_path):
    for fn in glob.glob(os.path.join(data_path, '*.mp4')):
        yield Document(uri=fn, id=os.path.basename(fn))


def check_search(resp: Request):
    for doc in resp.docs:
        print(f'Query text: {doc.text}')
        print(f'Matches:')
        for m in doc.matches:
            print(f'+- id: {m.id}, score: {m.scores["cosine"].value}, timestamp: {m.tags["timestamp"]}, link: {m.uri}')
        print('-'*10)


@click.command()
@click.option('--mode', '-m', type=click.Choice(['restful', 'grpc', 'restful_query', 'grpc_query']), default='grpc')
@click.option('--directory', '-d', type=click.Path(exists=True), default='toy_data')
def main(mode, directory):
    config()
    workspace = os.environ["JINA_WORKSPACE"]
    if os.path.exists(workspace) and mode not in ['restful_query', 'grpc_query']:
        print(
            f'\n +-----------------------------------------------------------------------------------+ \
              \n |                                   🤖🤖🤖                                           | \
              \n | The directory {workspace} already exists. Please remove it before indexing again. | \
              \n |                                   🤖🤖🤖                                           | \
              \n +-----------------------------------------------------------------------------------+'
        )
        return -1
    if mode == 'grpc':
        override_dict = {
            'protocol': 'grpc',
            'cors': False}
    else:
        override_dict = {}

    if mode in ['grpc', 'restful']:
        with Flow.load_config('index-flow.yml', override_with=override_dict) as f:
            f.post(on='/index', inputs=get_docs(directory), request_size=1)

    with Flow.load_config('search-flow.yml', override_with=override_dict) as f:
        if mode in ['grpc', 'grpc_query']:
            f.post(
                on='/search',
                inputs=DocumentArray([
                    Document(text='bicycle bell ringing'),
                    Document(text='typing on a keyboard'),
                    Document(text='a young girl'),
                ]),
                on_done=check_search)
        elif mode in ['restful', 'restful_query']:
            f.block()


if __name__ == '__main__':
    main()
