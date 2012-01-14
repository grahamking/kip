from setuptools import setup, find_packages

VERSION = __import__('kip').__version__

setup(
    name="kip",
    version=VERSION,
    author='Graham King',
    author_email='',
    description="kip Keeps Internet Passwords",
    packages=find_packages(),
    package_data={},
    scripts = ['kip.py'],
    url="https://github.com/grahamking/kip",
    install_requires=['setuptools'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities'
    ]
)
