#!/bin/bash

set -e 

rm -rf tst || true
mkdir tst
pushd tst
# test installation of module in virtual environment
virtualenv my-venv
source my-venv/bin/activate

pip3 install RogetThesaurus 

python3 ../tests/test_roget.py

echo "everything is fine. test passed"

deactivate

#rm -rf my-venv

popd tst
