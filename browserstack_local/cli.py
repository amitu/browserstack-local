import os
import sys
import stat
import zipfile
import os.path
import urllib2
import hashlib
import platform
import tempfile
import subprocess

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
			raise Exception("Unsupported archicteure for linux: %s" % arch)
	else:
		raise Exception("Unsopported operating system: %s" % os_name)

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

class TooManyDownloadAttemptsFailed(Exception): pass

def _download_file(url, filename):
	fd = file(filename, "w")
	fd.write(urllib2.urlopen(url).read())
	fd.close()
	if not check_file(url, filename):
		raise Exception("Check filed")

def download_file(url, filename):
	# tries to download/store the file 5 times
	# if failure in writing, instead of on network, this could be wasteful
	for i in range(5):
		try:
			_download_file(url, filename)
		except Exception, e:
			print "download failed", e, "retrying"
		else:
			return
	raise TooManyDownloadAttemptsFailed(e)

def check_file(url, filename):
	request = urllib2.Request(url)
	request.get_method = lambda : 'HEAD'
	response = urllib2.urlopen(request)
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
