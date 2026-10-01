# -*- mode: ruby -*-
# vi: set ft=ruby :

#Vagrant.require_version">= 2.2.14"

ipAdrPrefix = "192.168.56.100"
vcpus = 1
memory = 1024 # in Megabytes
cpuCap = 80

Vagrant.configure("2") do |config|
	config.vm.box = "bento/ubuntu-24.04"
	config.vm.provider "virtualbox" do |v|
		#v.gui = true
		v.name = "sd"
		v.cpus = vcpus
		v.memory = memory
		#v.customize ["modifyvm", :id, "--cpuexecutioncap", cpuCap]
		#v.customize ["modifyvm", :id, "--memory", memory.to_s]
		#v.customize ["modifyvm", :id, "--usb", "off"]
		#v.customize ["modifyvm", :id, "--usbehci", "off"]
		#v.update_guest_tools = true
  	end

	config.vm.network "forwarded_port", guest: 8000, host: 8000, host_ip: "127.0.0.1"
  	config.vm.network "private_network", ip: "#{ipAdrPrefix}"
  	config.vm.hostname = "sd"

  	config.vm.provision "shell" do |s|
		s.path = "./scripts/bootstrap.sh"
		s.args = "#{ipAdrPrefix}"
		s.privileged = false
	end
end
