#!/usr/bin/env python3
import os
import time
from common.params import Params

# for uploader
from selfdrive.loggerd.xattr_cache import getxattr, setxattr
import glob
import requests

# customisable values
GPX_LOG_PATH = '/data/media/0/gpx_logs/'
LOG_HERTZ = 1/10 # 0.1 Hz = 10 sec, higher for higher accuracy, 10hz seems fine

# uploader
UPLOAD_ATTR_NAME = 'user.upload'
UPLOAD_ATTR_VALUE = b'1'
LOG_PATH = '/data/media/0/gpx_logs/'

# osm api
API_HEADER = {'Authorization': 'Bearer 2pvUyXfk9vizuh7PwQFSEYBtFWcM-Pu7vxApUjSA0fc'}
VERSION_URL = 'https://api.openstreetmap.org/api/versions'
UPLOAD_URL = 'https://api.openstreetmap.org/api/0.6/gpx/create'

_DEBUG = False

def _debug(msg):
  if not _DEBUG:
    return
  print(msg, flush=True)

class GpxUploader():
  def __init__(self):
    self._delete_after_upload = not Params().get_bool('dp_gpxd')
    self._car_model = Params().get("dp_last_candidate", encoding='utf8')
    _debug("GpxUploader init - _delete_after_upload = %s" % self._delete_after_upload)
    _debug("GpxUploader init - _car_model = %s" % self._car_model)

  def _is_online(self):
    try:
      r = requests.get(VERSION_URL, headers=API_HEADER)
      _debug("is_online? status_code = %s" % r.status_code)
      return r.status_code >= 200
    except:
      return False

  def _get_is_uploaded(self, filename):
    _debug("%s is uploaded: %s" % (filename, getxattr(filename, UPLOAD_ATTR_NAME) is not None))
    return getxattr(filename, UPLOAD_ATTR_NAME) is not None

  def _set_is_uploaded(self, filename):
    _debug("%s set to uploaded" % filename)
    setxattr(filename, UPLOAD_ATTR_NAME, UPLOAD_ATTR_VALUE)

  def _get_files(self):
    return sorted( filter( os.path.isfile, glob.glob(LOG_PATH + '*') ) )

  def _get_files_to_be_uploaded(self):
    files = self._get_files()
    files_to_be_uploaded = []
    for file in files:
      if not self._get_is_uploaded(file):
        files_to_be_uploaded.append(file)
    return files_to_be_uploaded

  def _do_upload(self, filename):
    fn = os.path.basename(filename)
    data = {
      'description': "Routes from dragonpilot (%s)." % self._car_model,
      'visibility': 'identifiable'
    }
    files = {
      "file": (fn, open(filename, 'rb'))
    }
    try:
      r = requests.post(UPLOAD_URL, files=files, data=data, headers=API_HEADER)
      _debug("do_upload - %s - %s" % (filename, r.status_code))
      return r.status_code == 200
    except:
      return False

  def run(self):
    while True:
      files = self._get_files_to_be_uploaded()
      if len(files) == 0 or not self._is_online():
        _debug("run - not online or no files")
      else:
        for file in files:
          if self._do_upload(file):
            if self._delete_after_upload:
              _debug("run - _delete_after_upload")
              os.remove(file)
            else:
              _debug("run - set_is_uploaded")
              self._set_is_uploaded(file)
      # sleep for 300 secs if offroad
      # otherwise sleep 60 secs
      time.sleep(300 if Params().get_bool("IsOffroad") else 60)

def gpx_uploader_thread():
  gpx_uploader = GpxUploader()
  gpx_uploader.run()

def main():
  gpx_uploader_thread()

if __name__ == "__main__":
  main()
