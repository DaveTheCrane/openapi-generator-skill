# Implementation Plan: Customer Service API

## Overview

This plan implements the Customer Service REST API using the openapi-generator-maven-plugin with the delegate pattern. Implementation follows strict TDD (Red-Green-Refactor) where every piece of production code is driven by a failing test. The plan proceeds in three phases: (1) Maven build configuration and code generation, (2) delegate implementation driven by unit tests, and (3) integration tests verifying the full HTTP stack.

## Tasks

- [x] 1. Configure Maven build with openapi-generator-maven-plugin and dependencies
  - [x] 1.1 Add required Maven dependencies to pom.xml
    - Add `spring-boot-starter-webflux` dependency for reactive WebClient support
    - Add `org.openapitools:jackson-databind-nullable` dependency for nullable JSON field handling
    - Add `io.swagger.core.v3:swagger-annotations` dependency for Swagger annotations in generated code
    - Add `net.jqwik:jqwik:1.9.2` test dependency for property-based testing
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 1.2 Configure openapi-generator-maven-plugin with server execution
    - Add `openapi-generator-maven-plugin` (version 7.23.0) to pom.xml build plugins
    - Configure `CustomerApiServer` execution: generator `spring`, library `spring-boot`, delegatePattern=true
    - Set inputSpec to `${project.basedir}/specs/server/customer-service-openapi.yaml`
    - Set apiPackage to `com.example.kirogen.customerservice.server.api`
    - Set modelPackage to `com.example.kirogen.customerservice.server.data`
    - Configure `useSpringBoot3=true`, `useJakartaEe=true`
    - Set supportingFilesToGenerate to `ApiUtil.java`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.3 Configure openapi-generator-maven-plugin with Address Service client execution
    - Add `AddressApiWebClient` execution: generator `java`, library `webclient`
    - Set inputSpec to `${project.basedir}/specs/client/address-service-openapi.yaml`
    - Set apiPackage to `com.example.kirogen.customerservice.client.address.api`
    - Set modelPackage to `com.example.kirogen.customerservice.client.address.data`
    - Disable generateApiTests, generateModelTests, generateApiDocumentation, generateModelDocumentation
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 1.4 Configure openapi-generator-maven-plugin with Item Service client execution
    - Add `ItemServiceApiWebClient` execution: generator `java`, library `webclient`
    - Set inputSpec to `${project.basedir}/specs/client/item-service-openapi.yaml`
    - Set apiPackage to `com.example.kirogen.customerservice.client.item.api`
    - Set modelPackage to `com.example.kirogen.customerservice.client.item.data`
    - Disable all test and documentation generation flags
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 1.5 Verify build compiles successfully with all generated code
    - Run `mvn compile` and confirm it succeeds with server stubs and both client libraries generated
    - Verify generated sources appear in `target/generated-sources/openapi/`
    - Fix any dependency resolution or compilation errors
    - _Requirements: 1.6, 2.6, 2.7, 3.6, 9.4, 9.5_

- [x] 2. Checkpoint - Ensure build compiles with generated code
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Implement CustomersApiDelegateImpl — List Customers (TDD)
  - [x] 3.1 Write failing test: listCustomers returns HTTP 200 with two customers
    - Create `CustomersApiDelegateImplTest` test class
    - Write test asserting `listCustomers(null, null)` returns ResponseEntity with status 200
    - Assert the response body is a list with exactly 2 Customer objects
    - Run test — confirm it fails (Red)
    - _Requirements: 4.1, 4.2_

  - [x] 3.2 Implement minimum code to pass listCustomers test (Green)
    - Create `CustomersApiDelegateImpl` class annotated with `@Service` implementing `CustomersApiDelegate`
    - Override `listCustomers` to return hardcoded list of 2 Customer objects matching OpenAPI spec examples
    - Customer 1: cust-001, Jane Smith, Ms, +44 7700 900123, jane.smith@example.com, address addr-001
    - Customer 2: cust-002, John Doe, Mr, +1 555-0199, john.doe@example.com, address addr-002
    - Run test — confirm it passes
    - _Requirements: 4.1, 4.2_

  - [x] 3.3 Write failing test: listCustomers response contains all required Customer fields
    - Assert each Customer in list has non-null id, firstName, lastName, title, phone, email, address
    - Assert each address has non-null id, nameOrNumber, street, town, postCodeOrZip, country
    - Run test — confirm it fails (Red), then make it pass (Green)
    - _Requirements: 4.2_

  - [x] 3.4 Write failing test: listCustomers with page/size params returns same response
    - Assert `listCustomers(0, 10)` returns identical customer list as `listCustomers(null, null)`
    - Assert `listCustomers(5, 50)` also returns the same list
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 4.3, 4.4_

  - [x] 3.5 Write property test: pagination parameter invariance (Property 2)
    - **Property 2: Pagination parameter invariance**
    - Generate arbitrary valid Integer values for page and size parameters
    - Assert response always equals the response with null page/null size
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 4.3, 4.4**

  - [x] 3.6 Write property test: list response completeness (Property 1)
    - **Property 1: List response completeness**
    - Invoke listCustomers and verify every Customer in the response has all required non-null fields
    - Verify every nested Address has all required non-null fields (id, nameOrNumber, street, town, postCodeOrZip, country)
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 4.2**

- [ ] 4. Implement CustomersApiDelegateImpl — Get Customer by ID (TDD)
  - [x] 4.1 Write failing test: getCustomerById with "cust-001" returns HTTP 200 with correct data
    - Assert `getCustomerById("cust-001")` returns ResponseEntity with status 200
    - Assert the response body matches the hardcoded Customer 1 data (Jane Smith)
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 5.1_

  - [-] 4.2 Write failing test: getCustomerById with unknown valid ID returns HTTP 404
    - Assert `getCustomerById("cust-999")` returns ResponseEntity with status 404
    - Assert response body contains an Error object with status=404, non-null error, message, and timestamp
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 5.2_

  - [-] 4.3 Write failing test: getCustomerById with invalid format ID returns HTTP 400
    - Assert `getCustomerById("invalid/id!")` returns ResponseEntity with status 400
    - Assert response body contains an Error object with status=400, message about invalid format
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 5.3_

  - [~] 4.4 Write property test: unknown customer ID returns 404 (Property 3 — GET)
    - **Property 3: Unknown customer ID returns 404 (GET)**
    - Generate arbitrary strings matching `^[a-zA-Z0-9\-]+$` that are not "cust-001" or "cust-002"
    - Assert getCustomerById returns 404 with non-null Error fields (status, error, message, timestamp)
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 5.2**

  - [~] 4.5 Write property test: invalid customer ID format returns 400 (Property 4)
    - **Property 4: Invalid customer ID format returns 400**
    - Generate arbitrary strings containing special characters (spaces, slashes, unicode, etc.)
    - Assert getCustomerById returns 400 with non-null Error fields
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 5.3**

- [ ] 5. Implement CustomersApiDelegateImpl — Create Customer (TDD)
  - [~] 5.1 Write failing test: createCustomer with valid payload returns HTTP 201 with generated ID
    - Build a valid CustomerCreate object with all required fields
    - Assert `createCustomer(customerCreate)` returns ResponseEntity with status 201
    - Assert the response body has a non-null `id` field and all other fields matching the input
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 6.1, 6.2_

  - [~] 5.2 Write failing test: createCustomer with null/missing required fields returns HTTP 400
    - Construct a CustomerCreate with missing firstName (null)
    - Assert `createCustomer(invalidPayload)` returns ResponseEntity with status 400
    - Assert response body contains Error object with status=400
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 6.3_

  - [~] 5.3 Write property test: create returns complete customer with generated ID (Property 5)
    - **Property 5: Create returns complete customer with generated ID**
    - Generate arbitrary valid CustomerCreate payloads with all required fields
    - Assert POST returns 201 with a Customer object containing non-null id and all required fields
    - Assert the id field was not present in the request
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 6.1, 6.2**

- [ ] 6. Implement CustomersApiDelegateImpl — Update Customer (TDD)
  - [~] 6.1 Write failing test: updateCustomer with known ID "cust-001" returns HTTP 200
    - Build a valid CustomerCreate object
    - Assert `updateCustomer("cust-001", customerCreate)` returns ResponseEntity with status 200
    - Assert the response body has id="cust-001" and all required fields
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 7.1_

  - [~] 6.2 Write failing test: updateCustomer with unknown ID returns HTTP 404
    - Assert `updateCustomer("cust-999", customerCreate)` returns ResponseEntity with status 404
    - Assert response body contains Error object with status=404
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 7.2_

  - [~] 6.3 Write failing test: updateCustomer with invalid body returns HTTP 400
    - Construct a CustomerCreate with null required fields
    - Assert `updateCustomer("cust-001", invalidPayload)` returns ResponseEntity with status 400
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 7.3_

  - [~] 6.4 Write property test: unknown customer ID returns 404 (Property 3 — PUT)
    - **Property 3: Unknown customer ID returns 404 (PUT)**
    - Generate arbitrary strings matching `^[a-zA-Z0-9\-]+$` that are not "cust-001" or "cust-002"
    - Assert updateCustomer returns 404 with non-null Error fields
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 7.2**

- [ ] 7. Implement CustomersApiDelegateImpl — Delete Customer (TDD)
  - [~] 7.1 Write failing test: deleteCustomer with known ID "cust-001" returns HTTP 204
    - Assert `deleteCustomer("cust-001")` returns ResponseEntity with status 204
    - Assert the response body is null/empty
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 8.1_

  - [~] 7.2 Write failing test: deleteCustomer with unknown ID returns HTTP 404
    - Assert `deleteCustomer("cust-999")` returns ResponseEntity with status 404
    - Assert response body contains Error object with status=404, message mentioning the customer ID
    - Run test — confirm it fails (Red), then implement (Green)
    - _Requirements: 8.2_

  - [~] 7.3 Write property test: unknown customer ID returns 404 (Property 3 — DELETE)
    - **Property 3: Unknown customer ID returns 404 (DELETE)**
    - Generate arbitrary strings matching `^[a-zA-Z0-9\-]+$` that are not "cust-001" or "cust-002"
    - Assert deleteCustomer returns 404 with non-null Error fields
    - Use `@Property(tries = 100)` annotation
    - **Validates: Requirements 8.2**

- [~] 8. Checkpoint - Ensure all unit and property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Integration tests — full HTTP stack via MockMvc
  - [~] 9.1 Write integration test: GET /customers returns 200 with JSON array
    - Use `@SpringBootTest` and `MockMvc` to send GET request to `/customers`
    - Assert HTTP 200 status, content-type `application/json`, response body is a JSON array with 2 elements
    - Verify JSON structure matches OpenAPI Customer schema (all required fields present)
    - _Requirements: 4.1, 4.2_

  - [~] 9.2 Write integration test: GET /customers/{customerId} returns correct responses
    - Assert GET `/customers/cust-001` returns 200 with correct Customer JSON
    - Assert GET `/customers/cust-999` returns 404 with Error JSON
    - Assert GET `/customers/invalid!id` returns 400 with Error JSON
    - _Requirements: 5.1, 5.2, 5.3_

  - [~] 9.3 Write integration test: POST /customers returns 201
    - Send POST `/customers` with valid CustomerCreate JSON body
    - Assert HTTP 201 status and response body with generated `id` field
    - _Requirements: 6.1, 6.2_

  - [~] 9.4 Write integration test: PUT /customers/{customerId} returns correct responses
    - Assert PUT `/customers/cust-001` with valid body returns 200
    - Assert PUT `/customers/cust-999` with valid body returns 404
    - _Requirements: 7.1, 7.2_

  - [~] 9.5 Write integration test: DELETE /customers/{customerId} returns correct responses
    - Assert DELETE `/customers/cust-001` returns 204 with no body
    - Assert DELETE `/customers/cust-999` returns 404 with Error JSON
    - _Requirements: 8.1, 8.2_

- [~] 10. Final checkpoint - Ensure all tests pass and build succeeds
  - Run `mvn verify` to confirm full build including all tests passes
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using jqwik
- Unit tests validate specific examples and edge cases
- The TDD cycle (Red-Green-Refactor) is applied within each task — write a failing test first, then implement minimum code
- Generated code from openapi-generator-maven-plugin lives in `target/generated-sources/openapi/` and must not be committed to version control
- The delegate pattern separates concerns: generated controllers handle routing/validation, our delegate handles business logic

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5"] },
    { "id": 3, "tasks": ["3.1"] },
    { "id": 4, "tasks": ["3.2"] },
    { "id": 5, "tasks": ["3.3", "3.4"] },
    { "id": 6, "tasks": ["3.5", "3.6", "4.1"] },
    { "id": 7, "tasks": ["4.2", "4.3"] },
    { "id": 8, "tasks": ["4.4", "4.5", "5.1"] },
    { "id": 9, "tasks": ["5.2"] },
    { "id": 10, "tasks": ["5.3", "6.1"] },
    { "id": 11, "tasks": ["6.2", "6.3"] },
    { "id": 12, "tasks": ["6.4", "7.1"] },
    { "id": 13, "tasks": ["7.2"] },
    { "id": 14, "tasks": ["7.3"] },
    { "id": 15, "tasks": ["9.1", "9.2", "9.3", "9.4", "9.5"] }
  ]
}
```