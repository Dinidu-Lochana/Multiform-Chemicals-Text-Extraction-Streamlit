FROM openjdk:11-jre-slim
WORKDIR /app
# Download Tika server JAR
ADD https://downloads.apache.org/tika/tika-server-standard-2.9.2.jar tika-server.jar
EXPOSE 9998
CMD ["java", "-jar", "tika-server.jar", "-p", "9998", "-host", "0.0.0.0"]
