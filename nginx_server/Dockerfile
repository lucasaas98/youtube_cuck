FROM nginx:alpine
ARG SERVER_IP
ARG PORT
COPY nginx.conf /etc/nginx/nginx.conf
RUN sed -i 's/__SERVER_IP__/'"${SERVER_IP}"'/; s/__PORT__/'"${PORT}"'/' /etc/nginx/nginx.conf
RUN mkdir -p /www
COPY ./index.html /www
EXPOSE 80
