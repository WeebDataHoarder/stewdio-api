#!/usr/bin/env python3
from distutils.core import setup
import subprocess
import glob
import os

ver = os.environ.get("PKGVER") or subprocess.run(['git', 'describe', '--tags'], stdout=subprocess.PIPE).stdout.decode().strip()

reqs = []
with open('requirements.txt') as f:
    for l in f:
        if l.find("=") != -1:
            s = l.strip().split("=", 1)
            reqs.append("{} @ {}".format(s[1], s[0]))
        else:
            reqs.append(l.strip())

setup(
    name = 'stewdio',
    packages = [
        'stewdio',
        'stewdio.search',
        'stewdio.types',
        ],
    version = ver,
    description = 'Stewdio radio controller',
    author = 'minus',
    author_email = 'minus@mnus.de',
    url = 'https://git.sr.ht/~minus/stewdio-api',
    install_requires = reqs,
    license = 'MIT',
    package_data={
        'stewdio': [
            'templates/*.html',
        ] + [fn[len('stewdio/'):] for fn in glob.glob('stewdio/static/**', recursive=True)],
    },
)
