from setuptools import setup
setup(
    name = 'cfn_runner',
    version = '0.1.0',
    packages = ['cfn_runner'],
    license='mit',
    install_requires = ['boto3','pyyaml', 'deepmerge'],
    entry_points = {
        'console_scripts': [
            'cfn_runner = cfn_runner.__main__:main'
        ]
    })