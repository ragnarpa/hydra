import setuptools

setuptools.setup(
    name="hydra-ctl",
    version="0.0.1",
    author="Ragnar Paide",
    author_email="ragnar.paide@gmail.com",
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    entry_points={
        'console_scripts': ['hydra-ctl=hydra.manager.cli:main'],
    },
    install_requires=['docker', 'requests'],
    setup_requires=['wheel', 'pytest-runner'],
    tests_require=['pytest', 'pytest-mock']
)
