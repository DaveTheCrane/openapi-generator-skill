# Server Plugin Configuration

Add this `<execution>` block inside the `openapi-generator-maven-plugin` `<executions>` element.

Replace placeholders:
- `${ServiceName}` -- a descriptive name for this API (e.g. `Customer`, `Orders`)
- `${base.package}` -- your project's base package (e.g. `com.example.myservice`)

```xml
<plugin>
    <groupId>org.openapitools</groupId>
    <artifactId>openapi-generator-maven-plugin</artifactId>
    <version>7.23.0</version>
    <executions>

        <execution>
            <id>${ServiceName}ApiServer</id>
            <goals>
                <goal>generate</goal>
            </goals>
            <configuration>
                <inputSpec>
                    ${project.basedir}/spec/server/openapispec.yaml
                </inputSpec>
                <generateApiTests>true</generateApiTests>
                <generateModelTests>true</generateModelTests>
                <generateApiDocumentation>false</generateApiDocumentation>
                <generateModelDocumentation>false</generateModelDocumentation>
                <generatorName>spring</generatorName>
                <library>spring-boot</library>
                <apiPackage>${base.package}.server.api</apiPackage>
                <modelPackage>${base.package}.server.data</modelPackage>
                <supportingFilesToGenerate>ApiUtil.java</supportingFilesToGenerate>
                <invokerPackage>${base.package}</invokerPackage>
                <configOptions>
                    <interfaceOnly>false</interfaceOnly>
                    <useSpringBoot3>true</useSpringBoot3>
                    <delegatePattern>true</delegatePattern>
                    <useJakartaEe>true</useJakartaEe>
                </configOptions>
            </configuration>
        </execution>

    </executions>
</plugin>
```

## Configuration Explained

| Element | Purpose |
|---------|---------|
| `generatorName=spring` | Generates Spring MVC server code |
| `library=spring-boot` | Targets Spring Boot runtime |
| `delegatePattern=true` | Generates `*ApiDelegate` interfaces that you implement as `@Service` beans |
| `useSpringBoot3=true` | Targets Spring Boot 3.x / Spring Framework 6.x |
| `useJakartaEe=true` | Uses `jakarta.*` namespace (required for Spring Boot 3+) |
| `interfaceOnly=false` | Generates full controller classes (not just interfaces) that delegate to your beans |
| `supportingFilesToGenerate` | Limits supporting file generation to only `ApiUtil.java` |
| `generateApiTests=true` | Generates skeleton API test classes |
| `generateModelTests=true` | Generates skeleton model test classes |
| `generateApiDocumentation=false` | Skips API markdown documentation |
| `generateModelDocumentation=false` | Skips model markdown documentation |
