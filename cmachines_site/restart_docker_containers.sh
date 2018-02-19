docker ps -a | grep jinpengli/docker-image-reverse-ssh-tunnel | awk '{print $1}' | xargs docker restart
