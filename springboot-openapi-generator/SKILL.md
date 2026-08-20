---
name: springboot-openapi-generator
description: >
  Generates a RESTful Spring Boot microservice from an OpenAPI specification using the
  openapi-generator-maven-plugin with the delegate pattern. Use when asked to create a
  Spring Boot REST API from a Swagger/OpenAPI spec, scaffold a microservice, or generate
  server stubs and client libraries from OpenAPI definitions.
license: MIT
compatibility: Requires Java 21+, Maven 3.9+, and a Spring Boot project.
metadata:
  author: kiro
  version: "1.1"
  phase: "design, tasklist"
---

# Spring Boot OpenAPI Generator Skill

Generate a fully-wired Spring Boot RESTful microservice from an OpenAPI specification.
This skill uses `openapi-generator-maven-plugin` with the **delegate pattern** so that
all controller interfaces, models, and API boilerplate are generated at build time. You
only write business logic by implementing the generated delegate interfaces.

## When to Use

- User asks to create a Spring Boot REST microservice from an OpenAPI/Swagger spec
- User wants to avoid hand-writing controllers and DTOs
- User needs HTTP client libraries for downstream services

## Prerequisites

The target project must be a Maven-based Spring Boot application. The skill works with
any existing Spring Boot app -- it adds the openapi-generator plugin configuration to
the existing `pom.xml`.

## Folder Convention

OpenAPI specification files follow this layout relative to the project root:

```
project-root/
├── spec/
│   ├── server/
│   │   └── openapispec.yaml      # The server API spec
│   └── client/
│       └── <service>-openapispec.yaml  # One per downstream service
├── src/
│   └── main/java/...             # Business logic (delegates)
└── pom.xml
```

If the `spec/` directory structure does not exist, create it and place the provided
OpenAPI spec in the appropriate location.

## Step-by-Step Instructions

### 1. Place the OpenAPI Specification

- Put the server OpenAPI spec at `spec/server/openapispec.yaml`
- If client specs are provided, place each at `spec/client/<servicename>-openapispec.yaml`

### 2. Add Required Dependencies

Ensure the `pom.xml` includes at minimum:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc</artifactId>
</dependency>
```

Generated code frequently needs extra runtime dependencies beyond the starter (for
example a nullable-types module for `JsonNullable`, date/time (de)serializers for
generated WebClient clients, and annotation libraries). Do not assume the design's
dependency list is complete: when `mvn compile` reports a missing class, add the
dependency it needs and note it back in the design.

### 3. Configure the openapi-generator-maven-plugin

Add the plugin to the `<build><plugins>` section of `pom.xml`. Use the latest stable
version (7.23.0 or newer).

#### Server Generation (Required)

This execution generates the Spring server stubs with the delegate pattern. See
[references/server-plugin-config.md](references/server-plugin-config.md) for the
complete XML block.

Key configuration points:

- **generatorName**: `spring`
- **library**: `spring-boot`
- **delegatePattern**: `true` -- generates a `*ApiDelegate` interface per API tag
- **useSpringBoot3**: `true`
- **useJakartaEe**: `true`
- **interfaceOnly**: `false`
- **inputSpec**: `${project.basedir}/spec/server/openapispec.yaml`
- **apiPackage**: `<groupId>.server.api`
- **modelPackage**: `<groupId>.server.data`
- **supportingFilesToGenerate**: `ApiUtil.java`

The execution ID should be descriptive, e.g. `<ServiceName>ApiServer`.

#### Client Generation (Optional, repeatable)

For each downstream service, add an additional `<execution>` block. See
[references/client-plugin-config.md](references/client-plugin-config.md) for the
complete XML block.

Key configuration points:

- **generatorName**: `java`
- **library**: `webclient`
- **inputSpec**: `${project.basedir}/spec/client/<servicename>-openapispec.yaml`
- **apiPackage**: `<groupId>.client.<servicename>.api`
- **modelPackage**: `<groupId>.client.<servicename>.data`
- **No test or doc generation** (all set to `false`)

The execution ID should be descriptive, e.g. `<ServiceName>ApiWebClient`. When a client
execution writes to its own output directory, register that directory as a compile
source root (e.g. via `build-helper-maven-plugin`) so it is picked up by the build.

### 4. Implement Business Logic

After running `mvn compile`, the generated code appears in `target/generated-sources/`.

To implement business logic:

1. Create a Spring `@Service` class that implements the generated `*ApiDelegate` interface
2. Override the methods you need to implement
3. The generated controller will automatically delegate to your bean

Delegate methods should return the success body only. Handle error cases by throwing
exceptions (see "Error Handling" below), not by returning error models from the delegate.

Example:

```java
package com.example.myservice.delegate;

import com.example.myservice.server.api.PetsApiDelegate;
import com.example.myservice.server.data.Pet;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PetsApiDelegateImpl implements PetsApiDelegate {

    @Override
    public ResponseEntity<List<Pet>> listPets(Integer limit) {
        // Your business logic here
        return ResponseEntity.ok(List.of());
    }
}
```

### 5. Build and Verify

Run:

```bash
mvn clean compile
```

This triggers code generation. The generated sources are placed in
`target/generated-sources/openapi/` and are automatically added to the compile path.

## Working with Generated Types

Read the generated `.java` files under `target/generated-sources` before writing code or
tests against them — the real signatures often differ from the spec/design. Two recurring
quirks to expect:

- **Nullable fields generate as `JsonNullable<T>`, not `T`.** Fields that are optional or
  nullable in the spec are generated as
  `org.openapitools.jackson.nullable.JsonNullable<...>` (this requires the
  `jackson-databind-nullable` dependency). In tests, compare with `JsonNullable.of(value)`
  for a present value and `JsonNullable.<T>undefined()` for an absent one.
- **A generated `Error` model shadows `java.lang.Error`.** If the spec defines an `Error`
  schema, the generated type collides with the JDK's `java.lang.Error`. Import or fully
  qualify the generated type explicitly wherever you use it.

## Error Handling

Delegate methods return the success body type declared by the generated interface (for
example `ResponseEntity<Customer>` or `ResponseEntity<Void>`). Do NOT return an error
model from a delegate by casting through `ResponseEntity<?>` — that fights the generated
signature and leaks casts into production and test code.

Instead, use Spring's exception-handling mechanism:

1. Define hand-written exceptions for the error cases (e.g. `ResourceNotFoundException`).
2. In the delegate, THROW the exception for the error case and return the success body
   otherwise.
3. Add a hand-written `@RestControllerAdvice` (or `@ControllerAdvice`) that catches those
   exceptions and maps each to the appropriate HTTP status and the generated error model.

**Design this in from the start.** The design document MUST specify the error-handling
strategy: the exception types, which delegate operations throw them, and the advice that
maps exceptions to the generated error model and status codes. The task list MUST include
cycles for the advice and for each exception-to-response mapping.

Example:

```java
// Hand-written exception
public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) { super(message); }
}

// Delegate throws instead of returning an error body
@Override
public ResponseEntity<Pet> getPetById(String id) {
    Pet pet = lookup(id); // returns null if absent
    if (pet == null) {
        throw new ResourceNotFoundException("Pet with id '" + id + "' not found");
    }
    return ResponseEntity.ok(pet);
}

// Hand-written advice maps the exception to the generated Error model
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<com.example.myservice.server.data.Error> handleNotFound(
            ResourceNotFoundException ex, HttpServletRequest request) {
        var body = new com.example.myservice.server.data.Error()
                .status(404)
                .error("Not Found")
                .message(ex.getMessage())
                .timestamp(OffsetDateTime.now())
                .path(request.getRequestURI());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(body);
    }
}
```

Testing: unit-test the advice directly (instantiate it and call the handler), and
unit-test that delegates throw the expected exception for error cases. This keeps both
the delegate and the error mapping testable without a Spring context and without casts.

## Important Notes

- **Do NOT manually create controller classes, request/response DTOs, or API interfaces.**
  These are all generated by the plugin.
- The delegate pattern means the generated controller handles request routing and
  validation; your delegate handles business logic only.
- Delegates return success bodies and THROW for errors; a `@RestControllerAdvice` maps
  exceptions to the generated error model (see "Error Handling").
- Read the actual generated `.java` files before coding against them (see "Working with
  Generated Types").
- Generated code lives in `target/` and should NOT be committed to version control.
  Add `target/` to `.gitignore`.
- If the user provides an OpenAPI spec inline or as a file, place it in the correct
  `spec/` subfolder before configuring the plugin.
- When adding multiple client executions, each must have a unique `<id>` and distinct
  package names to avoid class collisions.

When building and compiling code, see also the instructions [here](./assets/build-and-codegen.md).
