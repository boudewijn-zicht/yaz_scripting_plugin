import os
import setuptools
import sys

with open("yaz_scripting_plugin/version.py") as file:
    globals = {}
    exec(file.read(), globals)
    version = globals["__version__"]

if sys.argv[-1] == "tag":
    os.system("git tag -a {} -m \"Release {}\"".format(version, version))
    os.system("git push origin {}".format(version))
    sys.exit()

if sys.argv[-1] == "publish":
    os.system("python3 setup.py sdist upload")
    os.system("python3 setup.py bdist_wheel upload")
    sys.exit()

setuptools.setup(
    name="yaz_scripting_plugin",
    packages=["yaz_scripting_plugin"],
    version=version,
    description="A plugin for YAZ providing shell scripting access",
    author="Boudewijn Schoon",
    author_email="yaz@frayja.com",
    url="https://github.com/yaz/yaz_scripting_plugin",
    license="MIT",
    install_requires=["yaz", "yaz_templating_plugin"],
    scripts=["bin/yaz-scripting", "bin/yaz-screen-wrapper"],
    zip_safe=False,
    test_suite="nose.collector",
    tests_require=["nose", "coverage"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6"
    ])
