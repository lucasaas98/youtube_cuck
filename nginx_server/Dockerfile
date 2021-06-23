FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /www
COPY ./index.html /www
RUN mkdir -p /data/videos/
RUN mkdir -p /data/thumbnails/
EXPOSE 80
COPY subscription_manager /data