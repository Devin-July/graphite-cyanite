# coding: utf-8
from setuptools import setup

setup(
    name='cyanite',
    version='0.4.7',
    url='https://github.com/coupang/graphite-cyanite',
    license='BSD',
    author='Bruno Renié',
    author_email='bruno@renie.fr',
    description=('A plugin for using graphite-web with the cassandra-based '
                 'Cyanite storage backend'),
    long_description=open('README.rst').read(),
    py_modules=('cyanite',),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    classifiers=(
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: System :: Monitoring',
    ),
    install_requires=(
        'requests>=2.25.0',
        'pylru>=1.2.0',
    ),
    python_requires='>=3.6',
    test_suite='tests',
)
