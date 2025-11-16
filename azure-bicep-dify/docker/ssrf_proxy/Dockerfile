FROM ubuntu/squid:latest

# Copy custom Squid configuration template
COPY squid.conf.template /etc/squid/squid.conf.template

# Create entrypoint script to substitute environment variables
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Substitute environment variables in the template\n\
envsubst < /etc/squid/squid.conf.template > /etc/squid/squid.conf\n\
\n\
# Start Squid\n\
exec squid -N -f /etc/squid/squid.conf\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Set default environment variables
ENV HTTP_PORT=3128 \
    COREDUMP_DIR=/var/spool/squid \
    REVERSE_PROXY_PORT="" \
    SANDBOX_HOST="" \
    SANDBOX_PORT=8194

# Expose proxy port
EXPOSE 3128

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]
