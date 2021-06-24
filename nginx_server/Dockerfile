FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /www
COPY ./index.html /www
EXPOSE 80