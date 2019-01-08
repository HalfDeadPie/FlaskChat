from setuptools import setup, find_packages

setup(
    name='FlaskChat',
    version='0.0.2',
    description='Distributed chat as a semestral work',
    author='Simon Stefunko',
    author_email='s.stefunko@gmail.com',
    keywords='chat, distributed, flask, school, semestral work, mi-dsv',
    license='Public Domain',
    url='https://github.com/HalfDeadPie/FlaskChat',
    packages=['flaskchat'],
    python_requires='~=3.5',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Programming Language :: Python',
        'Programming Language :: Python :: 5',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Framework :: Flask',
        'Environment :: Console',
        ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'flaskchat = flaskchat.__main__:runner',
        ],
    },
    install_requires=['Flask', 'click>=7', 'requests>=2.20.1']
)