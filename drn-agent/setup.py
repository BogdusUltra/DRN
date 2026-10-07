from setuptools import setup, find_packages

setup(
    name='drn-agent',
    version='0.1.0',
    description='Distributed Robotics Network Agent',
    packages=find_packages(),
    install_requires=[
        'rsa',
        'psutil'
    ],
    entry_points={
        'console_scripts': [
            'drn=drn_agent.cli:main',
        ],
    },
)
