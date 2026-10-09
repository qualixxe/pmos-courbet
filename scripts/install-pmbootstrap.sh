#!/usr/bin/env bash
#
# Install pmbootstrap into its own virtualenv.
#
# gitlab.postmarketos.org is behind Anubis, a proof-of-work gate that needs
# JavaScript, so the tool cannot be cloned from there by a CI runner. PyPI it is.
#
# Three separate things have bitten this step on different runners, so each is
# handled explicitly rather than assumed:
#
#   1. Debian and Ubuntu strip ensurepip out of python3 and ship it as a
#      separate python3-venv package, so `python3 -m venv` fails outright
#      without it. virtualenv is the fallback when it still does not work.
#   2. The system interpreter is externally managed under PEP 668, so a plain
#      pip install into it is refused. A venv is the answer to both at once.
#   3. pmbootstrap does not necessarily accept --version, so probing with it and
#      failing the build on a non-zero exit would be a false negative.
#
# usage: install-pmbootstrap.sh [install-dir]
set -euo pipefail

VENV="${1:-/opt/pmbootstrap}"

echo "::group::Preparing python for a virtualenv"
sudo apt-get update -qq || true
sudo apt-get install -y --no-install-recommends \
    python3-venv python3-virtualenv python3-pip || \
    echo "::warning::could not add the venv packages; falling back"
echo "::endgroup::"

if [ ! -d "$VENV" ]; then
    echo "::group::Creating $VENV"
    if ! sudo python3 -m venv "$VENV" 2>&1 | sed 's/^/  /'; then
        echo "::warning::python3 -m venv failed, trying virtualenv"
        sudo rm -rf "$VENV"
        sudo python3 -m virtualenv -p python3 "$VENV"
    fi
    echo "::endgroup::"
fi

PIP="$VENV/bin/pip"
PY="$VENV/bin/python"

if [ ! -x "$PIP" ]; then
    echo "::error::no pip inside $VENV - virtualenv was created without it"
    ls -la "$VENV/bin" || true
    exit 1
fi

echo "::group::Installing pmbootstrap"
sudo "$PIP" install --no-cache-dir --upgrade pip setuptools wheel
sudo "$PIP" install --no-cache-dir pmbootstrap
echo "::endgroup::"

# Put it on PATH for the later steps, which run under sudo -iu and do not
# inherit this shell's environment.
sudo mkdir -p /usr/local/bin
sudo ln -sf "$VENV/bin/pmbootstrap" /usr/local/bin/pmbootstrap

echo "::group::Verifying"
if command -v pmbootstrap >/dev/null 2>&1; then
    echo "pmbootstrap resolved to: $(command -v pmbootstrap)"
else
    echo "pmbootstrap is NOT on PATH; will be called by absolute path"
fi
# Do not fail on the probe itself: --version may not be supported.
"$VENV/bin/pmbootstrap" --version 2>/dev/null || \
    "$VENV/bin/pmbootstrap" --help >/dev/null 2>&1 || \
    echo "::warning::pmbootstrap ran but reported neither --version nor --help cleanly"
echo "pmbootstrap is installed and callable"
echo "::endgroup::"

# Report what we actually got, so a later failure is not a mystery.
sudo "$PIP" list 2>/dev/null | grep -i pmbootstrap || echo "  (pmbootstrap not visible in pip list)"
