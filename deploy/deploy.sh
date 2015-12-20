#!/bin/bash
source ~/urlbot-native/venv/bin/activate

ansible-playbook -i hosts deploy.yml --vault-password-file ~/.vaultpass -D
