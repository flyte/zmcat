import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="zmcat",
    version="0.0.5",
    author="Ellis Percival",
    author_email="zmcat@failcode.co.uk",
    description="A simple command line tool to test ZMQ push/pull/pub/sub soc"
        "kets. Based on https://github.com/lucasdicioccio/zmcat",
    license="UNLICENSE",
    keywords="zmq zeromq netcat nc 0mq",
    url="https://github.com/flyte/zmcat",
    packages=("zmcat",),
    install_requires=read("requirements.txt"),
    entry_points={
        "console_scripts": (
            "zmcat = zmcat.tool:main",
        )
    }
)
