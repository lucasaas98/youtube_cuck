echo " -> Creating Deployment Youtube Cuck"
kubectl apply -f yt-cuck-secrets.yml
kubectl apply -f mysql-pv.yml
kubectl apply -f youtube-cuck-pv.yml
sleep 5
kubectl apply -f yt-nginx-deployment.yml
kubectl apply -f mysql-deployment.yml
sleep 30
kubectl apply -f yt-backend-deployment.yml
kubectl apply -f yt-frontend-deployment.yml
echo " -> Deployment created"