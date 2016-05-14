import mock
import stat
import sys

import pytest

from browserstack_local import cli


def test_get_platform__unsupported_os(system):
    system.return_value = 'unsupported'
    with pytest.raises(Exception) as e:
        cli.get_platform()
    assert 'Unsupported operating system: unsupported' in e.value


def test_get_platform__unsupported_linux_architecture(mocker, system):
    system.return_value = 'linux'
    mocker.patch('platform.architecture', return_value=['unsupported'])
    with pytest.raises(Exception) as e:
        cli.get_platform()
    assert 'Unsupported architecture for linux: unsupported' in e.value


@pytest.mark.parametrize('arch, expected', [
    ('64bit', 'lin64'),
    ('32bit', 'lin32')
])
def test_get_platform__linux(mocker, arch, expected, system):
    system.return_value = 'linux'
    mocker.patch('platform.architecture', return_value=[arch])
    assert cli.get_platform() == expected


@pytest.mark.parametrize('os, expected', [
    ('windows', 'win'),
    ('darwin', 'mac')
])
def test_get_platform(os, expected, system):
    system.return_value = os
    assert cli.get_platform() == expected


def test_get_binary_url(mocker):
    mocker.patch('browserstack_local.cli.get_platform', return_value='mac')
    binary_url = ('https://www.browserstack.com/browserstack-local/'
                  'BrowserStackLocal-darwin-x64.zip')
    assert cli.get_binary_url() == binary_url


def test_get_binary_path__no_tmp_dir(mocker, cli_file):
    cli_file.side_effect = Exception('error')
    mocker.patch('tempfile.gettempdir', return_value='/tmpdir')
    path = cli.get_binary_path('https://foo.bar/filename')
    assert path == '/tmpdir/filename'


def test_get_binary_path(mocker, cli_file):
    mocker.patch('tempfile.gettempdir', return_value='tempdir')
    path = cli.get_binary_path('https://foo.bar/filename')
    assert path == '/tmp/filename'


def test_download_file(retrieve, check_file):
    cli._download_file('https://foo.bar/filename', 'testfile')
    retrieve.assert_called_once_with('https://foo.bar/filename', 'testfile')


def test_download_file__raises_exception(retrieve):
    retrieve.side_effect = Exception('err')
    with pytest.raises(Exception) as e:
        cli._download_file('https://foo.bar/filename', 'testfile')
    assert 'err' in str(e)


def test_download_file__checks_file(retrieve, check_file):
    check_file.reutrn_value = True
    cli._download_file('https://foo.bar/filename', 'testfile')
    check_file.assert_called_once_with('https://foo.bar/filename', 'testfile')


def test_download_file__invalid_file_raises_exception(retrieve, check_file):
    check_file.return_value = False
    with pytest.raises(Exception) as e:
        cli._download_file('https://foo.bar/filename', 'testfile')
    assert 'Check failed' in e.value


def test_download_file__retries_on_exception(mocker):
    download = mocker.patch('browserstack_local.cli._download_file')
    download.side_effect = Exception('failure')
    with pytest.raises(cli.TooManyDownloadAttemptsFailed):
        cli.download_file('https://foo.bar/filename', 'testfile')
    assert download.call_count == 5


def test_download_file__success(mocker):
    mocker.patch('browserstack_local.cli._download_file')
    result = cli.download_file('https://foo.bar/filename', 'testfile')
    assert result is None


def test_check_file__requests_url(cli_request, request_info):
    with pytest.raises(Exception):
        cli.check_file('https://foo.bar/filename', 'testfile')
    cli_request.assert_called_once_with('https://foo.bar/filename')


def test_check_file__makes_head_request(cli_request, request_info):
    with pytest.raises(Exception):
        cli.check_file('https://foo.bar/filename', 'testfile')
    assert cli_request.return_value.get_method() == 'HEAD'


def test_check_file__missing_etag(cli_request, request_info):
    with pytest.raises(Exception) as e:
        cli.check_file('https://foo.bar/filename', 'testfile')
    assert 'Etag not found on download url' in e.value


def test_check_file__reads_file(mocker, cli_request, request_info):
    request_info.return_value = {'ETag': '_tag_'}
    mocker.patch('hashlib.md5')
    mo = mock.mock_open(read_data=u'hashed_tag')
    with mock.patch.object(cli, 'open', mo):
        cli.check_file('https://foo.bar/filename', 'testfile')
    mo.assert_called_once_with('testfile', 'rb')


def test_check_file__generates_md5_hash(mocker, cli_request, request_info):
    request_info.return_value = {'ETag': '_tag_'}
    md5 = mocker.patch('hashlib.md5')
    mo = mock.mock_open(read_data=u'hashed_tag')
    with mock.patch.object(cli, 'open', mo):
        cli.check_file('https://foo.bar/filename', 'testfile')
    md5.assert_called_once_with('hashed_tag')


@pytest.mark.parametrize('tag, result', [('tag', True), ('invalid', False)])
def test_check_file__valid(mocker, cli_request, request_info, tag, result):
    request_info.return_value = {'ETag': '_tag_'}
    mocker.patch('hashlib.md5').return_value.hexdigest.return_value = tag
    mo = mock.mock_open(read_data=u'hashed_tag')
    with mock.patch.object(cli, 'open', mo):
        result = cli.check_file('https://foo.bar/filename', 'testfile')
    assert result == result


def test_ensure_binary__uses_existing_file_if_valid(
    mocker, binary_url, binary_path, check_file, download_file
):
    mocker.patch('os.path.isfile').return_value = True
    check_file.return_value = True
    cli.ensure_binary()
    assert download_file.call_count == 0


def test_ensure_binary__returns_existing_filename(
    mocker, binary_url, binary_path, check_file, download_file
):
    mocker.patch('os.path.isfile').return_value = True
    check_file.return_value = True
    result = cli.ensure_binary()
    assert result == binary_path.return_value


def test_ensure_binary__checks_existing_file(
    mocker, binary_url, binary_path, check_file, download_file
):
    mocker.patch('os.path.isfile').return_value = True
    check_file.return_value = False
    cli.ensure_binary()
    check_file.assert_called_once_with(
        binary_url.return_value,
        binary_path.return_value
    )


def test_ensure_binary__downloads_new_file_if_existing_invalid(
    mocker, binary_url, binary_path, check_file, download_file
):
    mocker.patch('os.path.isfile').return_value = True
    check_file.return_value = False
    cli.ensure_binary()
    download_file.assert_called_once_with(
        binary_url.return_value,
        binary_path.return_value
    )


def test_ensure_binary__downloads_missing_file(
    mocker, binary_url, binary_path, download_file
):
    mocker.patch('os.path.isfile').return_value = False
    cli.ensure_binary()
    download_file.assert_called_once_with(
        binary_url.return_value,
        binary_path.return_value
    )


def test_ensure_binary__returns_downloaded_filename(
    mocker, binary_url, binary_path, download_file
):
    mocker.patch('os.path.isfile').return_value = False
    result = cli.ensure_binary()
    assert result == binary_path.return_value


def test_unzip_binary__creates_zipfile(mocker):
    zipfile = mocker.patch('zipfile.ZipFile')
    mocker.patch('os.chmod')
    cli.unzip_binary('/path/to/binary')
    zipfile.assert_called_once_with('/path/to/binary')


def test_unzip_binary__extracts_zipfile(mocker):
    zipfile = mocker.patch('zipfile.ZipFile')
    zipfile.return_value.namelist.return_value = ['zipfile']
    mocker.patch('os.chmod')
    cli.unzip_binary('/path/to/binary')
    zipfile.return_value.extract.assert_called_once_with('zipfile', '/path/to')


def test_unzip_binary__changes_zipfile_permissions(mocker):
    zipfile = mocker.patch('zipfile.ZipFile')
    zipfile.return_value.namelist.return_value = ['zipfile']
    chmod = mocker.patch('os.chmod')
    cli.unzip_binary('/path/to/binary')
    chmod.assert_called_once_with(
        '/path/to/zipfile',
        stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE
    )


def test_unzip_binary__returns_zipfile_path(mocker):
    zipfile = mocker.patch('zipfile.ZipFile')
    zipfile.return_value.namelist.return_value = ['zipfile']
    mocker.patch('os.chmod')
    result = cli.unzip_binary('/path/to/binary')
    assert result == '/path/to/zipfile'


def test_launch_binary__command_line_args(mocker):
    binary = mocker.Mock()
    mocker.patch.object(sys, 'argv', ['cli.py', 'foo', 'bar'])
    subprocess_call = mocker.patch('subprocess.call')
    cli.launch_binary(binary)
    subprocess_call.assert_called_once_with([binary, 'foo', 'bar'])


def test_launch_binary(mocker):
    binary = mocker.Mock()
    mocker.patch.object(sys, 'argv', [])
    subprocess_call = mocker.patch('subprocess.call')
    cli.launch_binary(binary)
    subprocess_call.assert_called_once_with([binary])


def test_main__downloads_binary(mocker):
    download_binary = mocker.patch('browserstack_local.cli.ensure_binary')
    mocker.patch('browserstack_local.cli.unzip_binary')
    mocker.patch('browserstack_local.cli.launch_binary')
    cli.main()
    download_binary.assert_called_once_with()


def test_main__unzips_binary(mocker):
    download_binary = mocker.patch('browserstack_local.cli.ensure_binary')
    unzip_binary = mocker.patch('browserstack_local.cli.unzip_binary')
    mocker.patch('browserstack_local.cli.launch_binary')
    cli.main()
    unzip_binary.assert_called_once_with(download_binary.return_value)


def test_main__launches_binary(mocker):
    mocker.patch('browserstack_local.cli.ensure_binary')
    unzip_binary = mocker.patch('browserstack_local.cli.unzip_binary')
    launch_binary = mocker.patch('browserstack_local.cli.launch_binary')
    cli.main()
    launch_binary.assert_called_once_with(unzip_binary.return_value)
