#!/usr/bin/env bash
set -e

VAGRANT_HOME="/home/vagrant"
VENV_PATH="$VAGRANT_HOME/venv"

sudo timedatectl set-timezone America/Recife
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv

if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
python -m pip install "Django>=6.1,<6.2"

cd /vagrant
python manage.py migrate

if ! grep -q 'source /home/vagrant/venv/bin/activate' "$VAGRANT_HOME/.bashrc"; then
    printf '\nsource /home/vagrant/venv/bin/activate\ncd /vagrant\n' >> "$VAGRANT_HOME/.bashrc"
fi
