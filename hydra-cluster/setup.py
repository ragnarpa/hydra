import setuptools

setuptools.setup(
    name="hydra-cluster",
    version="0.0.1",
    author="Ragnar Paide",
    author_email="ragnar.paide@gmail.com",
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    entry_points={
        'console_scripts': ['hydra-cluster=hydra.cluster.api:main'],
    },
    install_requires=['Flask', 'docker', 'redis'],
    setup_requires=['wheel', 'pytest-runner'],
    tests_require=['pytest', 'pytest-mock']
)
