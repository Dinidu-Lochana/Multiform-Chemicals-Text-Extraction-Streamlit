# Use Java runtime
FROM openjdk:11-jre-slim

# Create working directory
WORKDIR /app

# Download Apache Tika server JAR (archived version 2.9.2)
ADD https://archive.apache.org/dist/tika/2.9.2/tika-server-standard-2.9.2.jar tika-server.jar

# Expose default port
EXPOSE 8080

# Run Tika server on cloud's dynamic port ($PORT)
CMD ["sh", "-c", "java -jar tika-server.jar -p $PORT -host 0.0.0.0"]
