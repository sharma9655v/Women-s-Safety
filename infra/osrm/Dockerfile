# Latest osrm-backend tag published on Docker Hub (v5.27.1 exists only as a
# GitHub release without an image; v5.25.0 is the newest published tag).
FROM osrm/osrm-backend:v5.25.0

COPY init-osrm.sh /opt/init-osrm.sh
RUN chmod +x /opt/init-osrm.sh

ENTRYPOINT ["/opt/init-osrm.sh"]