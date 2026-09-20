# Implementation Plan: Customer Service API

## Overview

Implement a Spring Boot 4.1.0 REST microservice exposing CRUD endpoints for customer resources. The controller returns hardcoded stub responses from OpenAPI examples. Reactive WebClient-based clients are provided for the Address Service and Item Service. Centralized error handling ensures consistent Error_Response formatting. Property-based tests validate correctness properties using jqwik.

## Tasks

- [x] 1. Set up project dependencies, configuration, and core data models
  - [x] 1.1 Add dependencies to pom.xml and configure application.yaml
    - Add `spring-boot-starter-webflux` dependency for WebClient support
    - Add `spring-boot-starter-validation` dependency for Jakarta Bean Validation
    - Add `net.jqwik:jqwik:1.9.2` test dependency
    - Add `com.squareup.okhttp3:mockwebserver` test dependency
    - Configure `server.port: 8080` and service base URLs in `application.yaml`
    - _Requirements: 10.1, 10.2, 10.4_

  - [x] 1.2 Create ServiceProperties configuration class
    - Create `com.example.kirogen.customerservice.config.ServiceProperties` with `@ConfigurationProperties(prefix = "services")`
    - Define `addressServiceBaseUrl` (default `http://localhost:8081`) and `itemServiceBaseUrl` (default `http://localhost:8082`)
    - Add `@EnableConfigurationProperties(ServiceProperties.class)` to main application class or config
    - _Requirements: 8.1, 9.1, 10.4_

  - [x] 1.3 Create server-side data models (Customer, CustomerCreate, Address, ErrorResponse)
    - Create `com.example.kirogen.customerservice.model.Customer` with Lombok annotations and all required fields
    - Create `com.example.kirogen.customerservice.model.CustomerCreate` with Jakarta `@NotNull` validation on all required fields
    - Create `com.example.kirogen.customerservice.model.Address` with nullable line1/line2 using `@JsonInclude(JsonInclude.Include.ALWAYS)`
    - Create `com.example.kirogen.customerservice.model.ErrorResponse` with status, error, message, timestamp, and optional path
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 1.4 Create client data models for Address Service and Item Service
    - Create `com.example.kirogen.customerservice.client.address.model.Address` and `AddressCreate`
    - Create `com.example.kirogen.customerservice.client.item.model.Item` and `ItemCreate`
    - All models use Lombok `@Data`, `@Builder`, `@AllArgsConstructor`, `@NoArgsConstructor`
    - _Requirements: 8.2, 8.3, 9.2, 9.3_

- [x] 2. Implement exception handling and controller
  - [x] 2.1 Create custom exceptions and GlobalExceptionHandler
    - Create `com.example.kirogen.customerservice.exception.CustomerNotFoundException`
    - Create `com.example.kirogen.customerservice.exception.InvalidParameterException`
    - Create `com.example.kirogen.customerservice.exception.GlobalExceptionHandler` with `@RestControllerAdvice`
    - Handle `InvalidParameterException` → 400, `CustomerNotFoundException` → 404, `MethodArgumentNotValidException` → 400, `HttpMessageNotReadableException` → 400, generic `Exception` → 500
    - Populate ErrorResponse with timestamp from `Instant.now().toString()` and path from `HttpServletRequest.getRequestURI()`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 2.2 Implement CustomerController with stubbed responses
    - Create `com.example.kirogen.customerservice.controller.CustomerController` with `@RestController` and `@RequestMapping("/customers")`
    - Implement `listCustomers` returning hardcoded two-customer array (Jane Smith cust-001, John Doe cust-002)
    - Validate `page >= 0` and `1 <= size <= 100`, throw `InvalidParameterException` on violation
    - Implement `createCustomer` returning hardcoded cust-003 response with 201 status
    - Implement `getCustomerById` validating ID against `^[a-zA-Z0-9\-]+$`, returning cust-001 stub or throwing `CustomerNotFoundException`
    - Implement `updateCustomer` validating ID and body, returning hardcoded updated response
    - Implement `deleteCustomer` validating ID, returning 204 or throwing `CustomerNotFoundException`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

  - [x] 2.3 Write MockMvc unit tests for CustomerController
    - Test GET /customers returns 200 with two customers
    - Test GET /customers with invalid pagination returns 400
    - Test POST /customers with valid body returns 201
    - Test POST /customers with missing fields returns 400
    - Test GET /customers/{id} with valid ID returns 200
    - Test GET /customers/{id} with invalid ID format returns 400
    - Test GET /customers/{id} with non-existent ID returns 404
    - Test PUT /customers/{id} returns 200 with updated stub
    - Test PUT /customers/{id} with invalid body returns 400
    - Test DELETE /customers/{id} returns 204
    - Test DELETE /customers/{id} with invalid ID returns 400
    - Test all error responses contain required ErrorResponse fields
    - _Requirements: 1.1, 1.4, 2.1, 2.3, 2.4, 3.1, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_

- [x] 3. Checkpoint - Ensure controller and error handling work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement WebClient configuration and service clients
  - [x] 4.1 Create WebClientConfig with named WebClient beans
    - Create `com.example.kirogen.customerservice.config.WebClientConfig` with `@Configuration`
    - Define `addressServiceWebClient` bean using `ServiceProperties.addressServiceBaseUrl`
    - Define `itemServiceWebClient` bean using `ServiceProperties.itemServiceBaseUrl`
    - _Requirements: 8.7, 9.7, 10.2_

  - [x] 4.2 Implement AddressServiceClient
    - Create `com.example.kirogen.customerservice.client.address.AddressServiceClient` with `@Component`
    - Inject `addressServiceWebClient` via constructor
    - Implement `listAddresses(Integer page, Integer size)` returning `Flux<Address>`
    - Implement `createAddress(AddressCreate payload)` returning `Mono<Address>`
    - Implement `getAddressById(String addressId)` returning `Mono<Address>`
    - Implement `updateAddress(String addressId, AddressCreate payload)` returning `Mono<Address>`
    - Implement `deleteAddress(String addressId)` returning `Mono<Void>`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 4.3 Implement ItemServiceClient
    - Create `com.example.kirogen.customerservice.client.item.ItemServiceClient` with `@Component`
    - Inject `itemServiceWebClient` via constructor
    - Implement `listItems(Integer page, Integer size, Boolean inStock)` returning `Flux<Item>`
    - Implement `createItem(ItemCreate payload)` returning `Mono<Item>`
    - Implement `getItemById(String itemId)` returning `Mono<Item>`
    - Implement `updateItem(String itemId, ItemCreate payload)` returning `Mono<Item>`
    - Implement `deleteItem(String itemId)` returning `Mono<Void>`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [x] 4.4 Write integration tests for service clients using MockWebServer
    - Test AddressServiceClient makes correct HTTP calls (1–2 representative operations)
    - Test ItemServiceClient makes correct HTTP calls (1–2 representative operations)
    - Verify correct URL construction and request/response serialization
    - _Requirements: 8.2, 8.3, 8.7, 9.2, 9.3, 9.7_

- [x] 5. Checkpoint - Ensure clients are wired correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Property-based tests for correctness properties
  - [x] 6.1 Write property test for valid customer ID acceptance
    - **Property 1: Customer ID validation accepts all valid IDs**
    - Generate random strings matching `^[a-zA-Z0-9\-]+$` using jqwik providers
    - Verify GET /customers/{id} does NOT return 400 for any valid ID
    - Use `@Property(tries = 100)` minimum
    - **Validates: Requirements 3.1, 4.1, 5.1**

  - [x] 6.2 Write property test for invalid customer ID rejection
    - **Property 2: Customer ID validation rejects all invalid IDs**
    - Generate random strings containing characters outside `[a-zA-Z0-9\-]` or empty strings
    - Verify GET /customers/{id} returns 400 for every generated invalid ID
    - **Validates: Requirements 3.3, 4.3, 5.2**

  - [x] 6.3 Write property test for pagination parameter validation
    - **Property 3: Pagination parameter validation**
    - Generate random (page, size) pairs where page < 0 OR size < 1 OR size > 100
    - Verify GET /customers returns 400 for each invalid combination
    - **Validates: Requirements 1.4**

  - [x] 6.4 Write property test for error response structure completeness
    - **Property 4: Error response structure completeness**
    - Generate various error-triggering requests (invalid IDs, bad pagination, missing fields)
    - Verify every error response contains status (integer), error (non-empty), message (non-empty), timestamp (ISO 8601)
    - **Validates: Requirements 6.1**

  - [x] 6.5 Write property test for JSON camelCase field names
    - **Property 5: JSON serialization preserves camelCase field names**
    - Serialize Customer objects with random data using Jackson ObjectMapper
    - Verify output contains exact field names: id, firstName, lastName, title, phone, email, address, nameOrNumber, postCodeOrZip
    - **Validates: Requirements 7.4**

  - [x] 6.6 Write property test for nullable field serialization
    - **Property 6: Nullable fields serialize as explicit null**
    - Serialize Address objects where line1 and/or line2 are null
    - Verify serialized JSON contains the keys "line1" and "line2" with JSON null values
    - **Validates: Requirements 7.3**

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties defined in the design document
- Unit tests validate specific examples and edge cases
- The design uses Java (Spring Boot 4.1.0, Java 21) — all code uses this language
- jqwik is the property-based testing framework for Java/JUnit 5
- MockWebServer is used for integration testing of WebClient-based clients

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2", "4.1"] },
    { "id": 4, "tasks": ["2.3", "4.2", "4.3"] },
    { "id": 5, "tasks": ["4.4", "6.1", "6.2", "6.3"] },
    { "id": 6, "tasks": ["6.4", "6.5", "6.6"] }
  ]
}
```