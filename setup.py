from setuptools import setup, find_packages
from django_tz import __version__
 
setup(
    name='django-tz',
    version=__version__,
    description='Django timezones localization app based on global cache (similar to django.utils.translation)',
    author='Rybarczyk Tomasz',
    author_email='paluho@gmail.com',
    packages=find_packages(),
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    install_requires=['pytz']
)
