import hashlib

import os
import os.path
import platform
import stat
import subprocess
import sys
import tempfile
try:
    from urllib.request import urlopen, Request, urlretrieve
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import urlretrieve
import zipfile


BINARIES = {
    "mac":   "BrowserStackLocal-darwin-x64.zip",
    "lin32": "BrowserStackLocal-linux-ia32.zip",
    "lin64": "BrowserStackLocal-linux-x64.zip",
    "win":   "BrowserStackLocal-win32.zip",
}


def get_platform():
    os_name = platform.system().lower()
    if os_name == "windows":
        return "win"
    elif os_name == "darwin":
        return "mac"
    elif os_name == "linux":
        arch = platform.architecture()[0]
        if arch == "64bit":
            return "lin64"
        elif arch == "32bit":
            return "lin32"
        else:
            raise Exception("Unsupported architecture for linux: %s" % arch)
    else:
        raise Exception("Unsupported operating system: %s" % os_name)


def get_binary_url():
    return "https://www.browserstack.com/browserstack-local/%s" % (
        BINARIES[get_platform()],
    )


def get_binary_path(url):
    filename = url.split("/")[-1]

    try:
        file("/tmp/.foo")
    except Exception:
        pass
    else:
        return "/tmp/%s" % filename

    tmpdir = tempfile.gettempdir()
    return os.path.join(tmpdir, filename)


class TooManyDownloadAttemptsFailed(Exception):
    pass


def _download_file(url, filename):
    try:
        urlretrieve(url, filename)
    except Exception as e:
        print("Could not write to {} due to: {}".format(filename, e))
        raise
    if not check_file(url, filename):
        raise Exception("Check failed")


def download_file(url, filename):
    """Attempts to download & store the file 5 times.

    If there is a failure in writing, instead of on network,
    this could be wateful.
    """
    exception = None
    for i in range(5):
        try:
            _download_file(url, filename)
        except Exception as e:
            print("download failed", e, "retrying")
            exception = e
        else:
            return
    raise TooManyDownloadAttemptsFailed(exception)


def check_file(url, filename):
    request = Request(url)
    request.get_method = lambda: 'HEAD'
    response = urlopen(request)
    etag = response.info().get("ETag")
    if not etag:
        raise Exception("Etag not found on download url")
    etag = etag[1:-1]
    md5hash = hashlib.md5(open(filename, 'rb').read()).hexdigest()
    return etag == md5hash


def ensure_binary():
    url = get_binary_url()
    filename = get_binary_path(url)

    if os.path.isfile(filename):
        if check_file(url, filename):
            return filename

    download_file(url, filename)
    return filename


def unzip_binary(binary):
    zfile = zipfile.ZipFile(binary)
    name = zfile.namelist()[0]
    (dirname, _) = os.path.split(binary)
    zfile.extract(name, dirname)
    filename = os.path.join(dirname, name)
    os.chmod(filename, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
    return filename


def launch_binary(binary):
    params = [binary]
    params.extend(sys.argv[1:])
    subprocess.call(params)


def main():
    binary = ensure_binary()
    binary = unzip_binary(binary)
    launch_binary(binary)


if __name__ == "__main__":
    main()
