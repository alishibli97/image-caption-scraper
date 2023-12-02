import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="image_caption_scraper",
    version="0.0.3",
    author="Ali Shibli",
    author_email="alishibli97@hotmail.com",
    description="image-caption-scraper is a Python tool for downloading images and captions from image search engines.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alishibli97/image-caption-scraper",
    project_urls={
        "Bug Tracker": "https://github.com/alishibli97/image-caption-scraper/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.11",
)