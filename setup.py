from setuptools import setup, find_packages
from codecs import open


def readme():
    with open("README.md", encoding="utf-8") as f:
        return f.read()


setup(
    name="lectocal-headless",
    version="1.0.0",
    author="Philip 'Hanse00' Mallegol-Hansen & Jens Jacob Thomsen (contrib)",
    author_email="philip@mallegolhansen.com",
    url="https://github.com/jensjacobt/LecToCal",
    description="Syncronize Lectio schedules to Google Calendar. Needs Firefox browser to be installed.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    license="Apache 2.0",
    python_requires=">=3",
    classifiers=[
        # Development Status
        "Development Status :: 5 - Production/Stable",
        # Audience / Topic
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Education",
        "Topic :: Utilities",
        "Topic :: Office/Business :: Scheduling",
        # Supported Versions
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        # Environment Type
        "Environment :: No Input/Output (Daemon)",
        "Environment :: Web Environment",
        # License
        "License :: OSI Approved :: Apache Software License",
    ],
    keywords="lectio google calendar sync utility",
    packages=find_packages(),
    install_requires=[
        "backoff",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "keyring",
        "lxml",
        "python-dateutil",
        "pytz",
        "selenium",
    ],
    package_data={
        "lectocal": [
            "credentials.json",
        ]
    },
    entry_points={"console_scripts": ["lectocal=lectocal.run:main"]},
)
