VAGRANT_HOME="/home/vagrant"

sudo timedatectl set-timezone America/Recife

sudo apt-get -y update

touch $VAGRANT_HOME/updated_ok
echo "update com sucesso" >> updated_ok
