from setuptools import setup, find_packages

with open('requirements.in') as fh:
    REQUIRES = fh.read()

setup(
    name='InstagramInfiniteScraper',
    version='0.1.0',
    packages=find_packages(),
    install_requires=REQUIRES,
    url='https://github.com/isaacimholt/InstagramInfiniteScraper',
    license='MIT License',
    author='Isaac Imholt',
    author_email='isaacimholt@gmail.com',
    description='OSINT tool for Instagram',
)
