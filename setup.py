from setuptools import setup

setup(name='yaz_scripting_plugin',
      version='1.0.0b1',
      description='A plugin for YAZ providing shell scripting access',
      author='Boudewijn Schoon',
      author_email='yaz@frayja.com',
      license='MIT',
      packages=['yaz_scripting_plugin'],
      install_requires=["yaz", "yaz_templating_plugin"],
      zip_safe=False)
