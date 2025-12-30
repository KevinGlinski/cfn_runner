from setuptools import setup
setup(
    name = 'cfn_runner',
    version = '0.2.0',
    packages = ['cfn_runner'],
    license='mit',
    install_requires = ['boto3>=1.42.18','pyyaml', 'deepmerge>=1.1.1'],
    entry_points = {
        'console_scripts': [
            'cfn_runner = cfn_runner.__main__:main'
        ]
    })