import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 6):
    raise ValueError("Requires Python 3.6 or superior")

from ees_sharepoint import __version__  # NOQA

install_requires = [
    "requests_ntlm",
    "elastic_enterprise_search",
    "pyyaml",
    "tika",
    "ecs_logging",
    "cerberus",
    "pytest",
]

description = ""

for file_ in ("README", "CHANGELOG"):
    with open("%s.rst" % file_) as f:
        description += f.read() + "\n\n"


classifiers = [
    "Programming Language :: Python",
    "License :: OSI Approved :: Apache Software License",
    "Development Status :: 5 - Production/Stable",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
]


setup(
    name="ees-sharepoint",
    version=__version__,
    url="someurl",
    packages=find_packages(),
    long_description=description.strip(),
    description=("Some connectors"),
    author="author",
    author_email="email",
    include_package_data=True,
    zip_safe=False,
    classifiers=classifiers,
    install_requires=install_requires,
    data_files=[("config", ["sharepoint_connector_config.yml"])],
    entry_points="""
      [console_scripts]
      bootstrap = ees_sharepoint.cmd:bootstrap
      test_connectivity = ees_sharepoint.cmd:test_connectivity
      full_sync = ees_sharepoint.cmd:full_sync
      incremental_sync = ees_sharepoint.cmd:incremental_sync
      deletion_sync = ees_sharepoint.cmd:deletion_sync
      permission_sync = ees_sharepoint.cmd:permission_sync
      """,
)
