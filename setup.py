import setuptools
import os

setuptools.setup(
    name="tipset",
    version="0.0.8",
    author="Xiao Liang",
    author_email="xiliang@redhat.com",
    description="tipset is a colletion of mini tools about various tips under linux.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/liangxiao1/tipset",
    #packages=setuptools.find_packages(),
    packages=[ 'tipset','tipset.libs'],
    package_data={
        'tipset': [
            'data/*',
        ]
    },
    include_package_data=True,
    install_requires=['argparse'],
    license="GPLv3+",
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        "Programming Language :: Python :: 3",
        'Operating System :: POSIX',

    ],
    python_requires='>=3.6',
    entry_points = {
             'console_scripts': [
                 'tipsearch = tipset.tipsearch:main',
                 'json_parser = tipset.json_parser:main',
                 'aws_amis_search = tipset.aws_amis_search:main',
                 'aws_instance_search = tipset.aws_instance_search:main'
             ],
         },
)
