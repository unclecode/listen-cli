from setuptools import setup, find_packages

requirements = []
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='listen-cli',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'listen=listen_cli.script:main',
        ],
    },
    author="Unclecode",
    author_email="unclecode@kidocode.com",
    description='A script to transcribe audio from various sources using different engines',
    url='https://github.com/unclecode/listen-cli',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
