#!/bin/bash
set -e
THIS_DIR=$(dirname $0)
BUNDLE_CONTENTS_DIR=${THIS_DIR}/dist/Accounting.app/Contents
BUNDLE_MACOS_DIR=${BUNDLE_CONTENTS_DIR}/MacOS
RESOURCE_DIR=${THIS_DIR}/resources
${RESOURCE_DIR}/build_resources.sh

# When using pyenv virtualenv the Python interpreter must be build with shared option enabled.
# $ env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.6.4
# See http://pyinstaller.readthedocs.io/en/latest/development/venv.html?highlight=shared
#
# Extended debug while building/running application:
# --log-level=DEBUG --debug
pyinstaller --icon ${RESOURCE_DIR}/icon.icns \
            --onefile --windowed --noconfirm --clean \
            -n Accounting \
            --hidden-import=jinja2.ext \
            --paths ${THIS_DIR} \
            ${THIS_DIR}/accounting/gui/main.py

# Add support for high DPI aka retina displays
INFO_PLIST=${BUNDLE_CONTENTS_DIR}/Info.plist
plutil -insert NSPrincipalClass -string NSApplication ${INFO_PLIST}
plutil -insert NSHighResolutionCapable -string True ${INFO_PLIST}
