from setuptools import setup, find_packages
from setuptools.command.install import install as _install
import os
import sys
import subprocess

# Function to read the requirements.txt file
def read_requirements(file):
    with open(file, 'r') as f:
        return f.read().splitlines()

# Path to the requirements.txt file
requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')

# Read the requirements
requirements = read_requirements(requirements_path)

# Custom install command to run the post-install script
class CustomInstallCommand(_install):
    def run(self):
        _install.run(self)
        subprocess.run([sys.executable, 'post_install.py'], check=True)


setup(
    name='pleiades',
    version='0.1',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            # Add command line scripts if needed, e.g.,
        ],
    },
    author='Alex M. Long',
    author_email='alexlong@lanl.gov',
    description='Python Libraries Extensions for Isotopic Analysis via Detailed Examination of SAMMY',
    url='https://github.com/lanl/Pleiades',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    cmdclass={
    'install': CustomInstallCommand,
    },
    package_data = {'nucDataLibs':['*/*']},
    license="MIT",
    python_requires='>=3.7',
)
