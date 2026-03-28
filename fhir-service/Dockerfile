FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/fhir-service-*.jar /app/app.jar
EXPOSE 8001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
