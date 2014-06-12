from setuptools import setup

setup(
    name='browserstack-local',
    version='0.2',
    description='Browserstack Local',
    author='Amit Upadhyay',
    author_email='amitu@rrowserstack.com',
    url='http://github.com/amitu/browserstack-local',
    packages=['browserstack_local'],
        entry_points = {
        'console_scripts': ['browserstack-local=browserstack_local:main'],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)
