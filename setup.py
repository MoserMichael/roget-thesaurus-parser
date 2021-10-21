import os
import setuptools 

def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()

setuptools.setup(
    name = "RogetThesaurus", 
    version = "0.0.8",
    author = "Michael Moser",
    author_email = "moser.michael@gmail.com",
    description = ("API to the Roget thesaurus"),
    license = "BSD",                                                                
    keywords = "natural language processing; thesaurus",
    url = "https://github.com/MoserMichael/roget-thesaurus-parser",
    packages=setuptools.find_packages(),
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        "Natural Language :: English",
	"Topic :: Text Processing :: Linguistic",
        "Intended Audience :: Science/Research",
	"Intended Audience :: Developers",
 	"Operating System :: OS Independent",
	"License :: OSI Approved :: BSD License",
    ],
    python_requires='>=3.6',
)
