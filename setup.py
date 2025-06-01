import os
import sys
from setuptools import setup  # Moved to top

if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    sys.exit()

# Hackishly inject a constant into builtins to enable importing of the
# package before the library is built.
if sys.version_info[0] < 3:
    import __builtin__ as builtins
else:
    import builtins
builtins.__FEEDFINDER2_SETUP__ = True
import feedfinder2  # noqa: E402

setup(
    name="feedfinder2",
    version=feedfinder2.__version__,
    url="https://github.com/dfm/feedfinder2",
    license={"file": "LICENSE"},
    author="Dan Foreman-Mackey",
    author_email="foreman.mackey@gmail.com",
    description="Find the feed URLs for a website.",
    long_description=open("README.rst").read(),
    py_modules=["feedfinder2"],
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
