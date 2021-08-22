#!/bin/bash -ixe


rm -rf dist || true

python3 -m pydoc -w ./rogetapi/roget_parser.py                                                                                                                                              

python3 setup.py sdist bdist_wheel

python3 -m pip install --user --upgrade twine

# twine is put here right now, so add it to path.
export PATH=$HOME/Library/Python/3.9/bin:$PATH

twine check dist/*


cat <<EOF
*** upload ***
enter user: __token__
for password: <pypi api token>
EOF

#python3 -m twine upload --repository testpypi --verbose dist/*
python3 -m twine upload --verbose dist/*




