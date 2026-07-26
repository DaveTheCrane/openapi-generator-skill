# Client Plugin Configuration

Add one `<execution>` block per downstream service inside the same
`openapi-generator-maven-plugin` `<executions>` element that contains the server
execution.

Replace placeholders:
- `${ServiceName}` -- a descriptive name for the downstream service (e.g. `User`, `Billing`)
- `${servicename}` -- lowercase version used in package paths (e.g. `user`, `billing`)
- `${base.package}` -- your project's base package (e.g. `com.example.myservice`)
- `${specfilename}` -- the OpenAPI spec filename (e.g. `userservice-openapispec.yaml`)

```xml
<execution>
    <id>${ServiceName}ApiWebClient</id>
    <goals>
        <goal>generate</goal>
    </goals>
    <configuration>
        <inputSpec>
            ${project.basedir}/spec/client/${specfilename}
        </inputSpec>
        <generateApiTests>false</generateApiTests>
        <generateModelTests>false</generateModelTests>
        <generateApiDocumentation>false</generateApiDocumentation>
        <generateModelDocumentation>false</generateModelDocumentation>
        <generatorName>java</generatorName>
        <library>webclient</library>
        <apiPackage>${base.package}.client.${servicename}.api</apiPackage>
        <modelPackage>${base.package}.client.${servicename}.data</modelPackage>
    </configuration>
</execution>
```

## Configuration Explained

| Element | Purpose |
|---------|---------|
| `generatorName=java` | Generates a Java HTTP client library |
| `library=webclient` | Uses Spring WebClient (reactive, non-blocking) as the HTTP transport |
| `generateApiTests=false` | No test generation for client code |
| `generateModelTests=false` | No test generation for client models |
| `generateApiDocumentation=false` | No documentation generation |
| `generateModelDocumentation=false` | No documentation generation |

## Notes

- Repeat this entire `<execution>` block for each downstream microservice.
- Each execution must have a **unique `<id>`**.
- Use distinct package names (`client.<servicename>.api` / `client.<servicename>.data`)
  to prevent class name collisions between different client libraries.
- The generated client classes can be injected as Spring beans. Configure a `WebClient`
  bean with the appropriate base URL for each downstream service.

## Example: Multiple Clients

If your service calls both a User service and a Billing service:

```xml
<executions>
    <!-- Server execution (see server-plugin-config.md) -->
    <execution>
        <id>MyServiceApiServer</id>
        ...
    </execution>

    <!-- Client for User service -->
    <execution>
        <id>UserApiWebClient</id>
        <goals><goal>generate</goal></goals>
        <configuration>
            <inputSpec>${project.basedir}/spec/client/userservice-openapispec.yaml</inputSpec>
            <generatorName>java</generatorName>
            <library>webclient</library>
            <apiPackage>com.example.myservice.client.user.api</apiPackage>
            <modelPackage>com.example.myservice.client.user.data</modelPackage>
            <generateApiTests>false</generateApiTests>
            <generateModelTests>false</generateModelTests>
            <generateApiDocumentation>false</generateApiDocumentation>
            <generateModelDocumentation>false</generateModelDocumentation>
        </configuration>
    </execution>

    <!-- Client for Billing service -->
    <execution>
        <id>BillingApiWebClient</id>
        <goals><goal>generate</goal></goals>
        <configuration>
            <inputSpec>${project.basedir}/spec/client/billingservice-openapispec.yaml</inputSpec>
            <generatorName>java</generatorName>
            <library>webclient</library>
            <apiPackage>com.example.myservice.client.billing.api</apiPackage>
            <modelPackage>com.example.myservice.client.billing.data</modelPackage>
            <generateApiTests>false</generateApiTests>
            <generateModelTests>false</generateModelTests>
            <generateApiDocumentation>false</generateApiDocumentation>
            <generateModelDocumentation>false</generateModelDocumentation>
        </configuration>
    </execution>
</executions>
```
