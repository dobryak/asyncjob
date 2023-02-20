from asyncjob import (
    __version__,
    __license__,
    __author__,
    __author_email__,
    __url__,
)

from setuptools import setup, find_packages


def get_install_requires():
    install_requires = []

    with open("requirements.txt", "r") as fp:
        for pkg in fp:
            install_requires.append(pkg)

    return install_requires


setup(
    name="asyncjob",
    description="asyncjob is another simple scheduler for asyncio jobs",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url=__url__,
    author=__author__,
    author_email=__author_email__,
    version=__version__,
    license=__license__,
    packages=find_packages(),
    package_data={"asyncjob": ["py.typed"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    install_requires=get_install_requires(),
    python_requires=">=3.10",
)
