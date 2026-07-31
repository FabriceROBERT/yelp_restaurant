# Image Spark du projet = image Bitnami officielle + Pillow (décodage/hash
# d'images, nécessaire pour la transformation Silver des photos - absent de
# l'image de base) + driver JDBC PostgreSQL (écriture des KPIs Gold depuis
# Spark - absent aussi). Construite localement pour rester 100% automatisé
# (pas de `docker exec pip install` manuel, qui ne survivrait pas à un rebuild).
FROM bitnamilegacy/spark:3.5.6

USER root
RUN pip install --no-cache-dir Pillow==11.* \
    && curl -fsSL -o /opt/bitnami/spark/jars/postgresql-42.7.4.jar \
       https://jdbc.postgresql.org/download/postgresql-42.7.4.jar
USER 1001
