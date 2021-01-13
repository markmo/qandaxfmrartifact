import setuptools

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='qandaxfmrartifact',
    version='0.0.9',
    author='Mark Moloney',
    author_email='m4rkmo@gmail.com',
    description='BentoML artifact framework for Q&A Transformers',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/markmo/qandaxfmrartifact',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        # 'BentoML==0.10.1',
        # 'transformers==2.10.0',
    ],
    python_requires='>=3.6',
)
