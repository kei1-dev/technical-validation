FROM nginx:alpine

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY proxy_params /etc/nginx/proxy_params

# Default environment variables
ENV DIFY_WEB_HOST=dify-dev-web.internal.azurecontainerapps.io
ENV DIFY_WEB_PORT=80
ENV DIFY_API_HOST=dify-dev-api.internal.azurecontainerapps.io
ENV DIFY_API_PORT=80

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
