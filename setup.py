from setuptools import setup

setup(name="upshatmonitor",
      version="0.1.0",
      description="Monitor of UPS HAT For Raspberry Pi",
      author="Andrey Shertsinger",
      url='https://githum.com/karakum/ups-hat-monitor',
      author_email="andrey@shertsinger.ru",
      package_dir={'': 'src'},
      packages=['upshatmonitor', ],
      entry_points={
          'console_scripts': [
              'ups-hat-monitor=upshatmonitor:main ',
          ],
      },
      install_requires=[
          'smbus2',
      ],
      long_description="",
      data_files=[]
      )
