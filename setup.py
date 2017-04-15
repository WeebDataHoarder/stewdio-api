#!/usr/bin/env python3
from distutils.core import setup
import subprocess
import glob
import os

ver = os.environ.get("PKGVER") or subprocess.run(['git', 'describe', '--tags'],
      stdout=subprocess.PIPE).stdout.decode().strip()

setup(
  name = 'radiodb',
  packages = [
      'radiodb',
      'radiodb.types',
      'radiodb.alembic',
      'radiodb.alembic.versions'
  ],
  version = ver,
  description = 'radio.stew.moe database bindings',
  author = 'Drew DeVault',
  author_email = 'sir@cmpwn.com',
  url = 'https://git.sr.ht/~sircmpwn/radiodb',
  install_requires = [
      'sqlalchemy',
      'sqlalchemy-utils',
      'werkzeug'
  ],
  license = 'WTFPL'
)
