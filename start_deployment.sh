echo " -> Creating Deployment Youtube Cuck"
microk8s kubectl apply -f yt-cuck-secrets.yml
microk8s kubectl apply -f mysql-pv.yml
microk8s kubectl apply -f youtube-cuck-pv.yml
sleep 20
microk8s kubectl apply -f yt-nginx-deployment.yml
microk8s kubectl apply -f mysql-deployment.yml
sleep 60
microk8s kubectl apply -f yt-backend-deployment.yml
microk8s kubectl apply -f yt-frontend-deployment.yml
echo " -> Deployment created"
