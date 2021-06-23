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

sleep 10
echo " -> Copying subscription file to volume"
nice=$(kubectl get pods --selector=app=yt-nginx -o jsonpath='{.items[0].metadata.name}')
kubectl cp nginx_server/subscription_manager $nice:/data
echo " -> Create dirs inside volume"
kubectl exec $nice -- mkdir /data/thumbnails
kubectl exec $nice -- mkdir /data/videos

sleep 20
service_ip=$(minikube service yt-cuck-nginx --url=true)
echo $service_ip > ip.txt
kubectl cp ip.txt $nice:/data
echo " -> Deployment created"