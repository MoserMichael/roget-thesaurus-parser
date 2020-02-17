#!/bin/bash -ex

# get import name
IMPORT_NAME=`cat setup.py  | sed -n s'/.*name = "\([^"]*\)",.*$/\1/p'`

pip uninstall -y RogetThesaurus  || true
pip install -i https://test.pypi.org/simple/ RogetThesaurus --user
python3 tests/test_roget.py


# create empty virtual environment dir
#rm -rf ./venv-dir || true

# virtual env.
#python3 -m venv venv-dir

# install into virtual environment
#bash -cxe "source ./venv-dir/bin/activate; cd ./venv-dir; which pip; pip install --upgrade setuptools; pip install https://test.pypi.org/simple/ ${IMPORT_NAME}"

#$VDIR/bin/python tests/test_roget.py
