import pytest

from browserstack_local import cli


@pytest.fixture
def system(mocker):
    return mocker.patch('platform.system')


@pytest.fixture
def isdir(mocker):
    return mocker.patch('os.path.isdir')


@pytest.fixture
def check_file(mocker):
    return mocker.patch('browserstack_local.cli.check_file')


@pytest.fixture
def cli_request(mocker):
    return mocker.patch.object(cli, 'Request')


@pytest.fixture
def request_info(mocker):
    response_info = mocker.patch.object(cli, 'urlopen').return_value.info
    response_info.return_value = {}
    return response_info


@pytest.fixture
def retrieve(mocker):
    return mocker.patch.object(cli, 'urlretrieve')


@pytest.fixture
def binary_url(mocker):
    return mocker.patch('browserstack_local.cli.get_binary_url')


@pytest.fixture
def binary_path(mocker):
    return mocker.patch('browserstack_local.cli.get_binary_path')


@pytest.fixture
def download_file(mocker):
    return mocker.patch('browserstack_local.cli.download_file')
