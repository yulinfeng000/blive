import setuptools

with open("./README.md", "r") as f:
    description = f.read()

setuptools.setup(
    name="blive",
    version="0.1.0",
    author="cam",
    author_email="yulinfeng000@gmail.com",
    long_description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/yulinfeng000/blive",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    install_requires=["aiohttp","requests","APScheduler==3.9.1","brotli","pyee"]
)
