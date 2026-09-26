# Implementation Plan: Customer Service API

## Overview

This plan implements the Customer Service REST API following strict TDD (Red-Green-Refactor) with hexagonal architecture. The execution order prioritizes components with the most edge cases first: Model classes → GlobalExceptionHandler → CustomerService → CustomerController → AddressServiceClient → ItemServiceClient. Each task produces a failing test first, then the minimal implementation to make it pass.

## Tasks

- [ ] 1. Add dependencies and configure project
  - [ ] 1.1 Add required Maven dependencies to pom.xml
    - Add `spring-boot-starter-webflux` for reactive WebClient
    - Add `spring-boot-starter-validation` for Bean Validation
    - Add `net.jqwik:jqwik:1.9.2` (test scope) for property-based testing
    - Add `com.squareup.okhttp3:mockwebserver` (test scope) for client tests
    - _Requirements: 7.1, 8.3, 9.2_
  - [ ] 1.2 Configure application.yaml with client base URLs
    - Add `client.address-service.base-url: http://localhost:8081`
    - Add `client.item-service.base-url: http://localhost:8082`
    - _Requirements: 7.1, 8.1_

- [ ] 2. Implement model classes (TDD)
  - [ ] 2.1 Implement ErrorResponse model
    - Write test verifying JSON serialization of all five fields (status, error, message, timestamp, path)
    - Implement `ErrorResponse` with Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
    - _Requirements: 6.1, 9.7_
  - [ ] 2.2 Implement Address model with null-field serialization
    - Write test verifying that `line1` and `line2` serialize as JSON `null` (key present with null value) rather than being omitted
    - Write test verifying required fields serialize correctly
    - Implement `Address` with `@JsonInclude(JsonInclude.Include.ALWAYS)` and validation annotations
    - _Requirements: 9.3, 9.4_
  - [ ] 2.3 Implement Customer model
    - Write test verifying JSON serialization of all fields including nested Address
    - Implement `Customer` with Lombok annotations
    - _Requirements: 9.1_
  - [ ] 2.4 Implement CustomerCreate model with validation annotations
    - Write test verifying `@NotBlank` on firstName, lastName, title, phone; `@NotBlank @Email` on email; `@NotNull @Valid` on address
    - Implement `CustomerCreate` with Bean Validation annotations
    - _Requirements: 9.2, 10.1, 10.2, 10.3, 10.6, 10.7_
  - [ ] 2.5 Implement Item and ItemCreate models
    - Write test verifying Item serialization round-trip (serialize → deserialize produces equal object)
    - Write test verifying ItemCreate validation annotations (`@NotBlank`, `@Min(0)`, `@NotNull`)
    - Implement `Item` and `ItemCreate` with Lombok and validation annotations
    - _Requirements: 9.5, 9.6_
  - [ ] 2.6 Implement AddressCreate model
    - Write test verifying serialization and validation annotations
    - Implement `AddressCreate` with Lombok and `@NotBlank` annotations
    - _Requirements: 7.4, 7.5_
  - [ ]* 2.7 Write property test for null address field serialization
    - **Property 10: Null address fields serialize as JSON null**
    - **Validates: Requirements 9.4**
  - [ ]* 2.8 Write property test for Item serialization round-trip
    - **Property 9: Item model serialization round-trip**
    - **Validates: Requirements 8.4, 9.5**

- [ ] 3. Implement GlobalExceptionHandler (TDD)
  - [ ] 3.1 Implement CustomerNotFoundException and handler
    - Write test: when `CustomerNotFoundException` is thrown, response is 404 with Error_Response containing "Not Found" and message "Customer with id '{id}' not found"
    - Create `CustomerNotFoundException` class and handler method in `GlobalExceptionHandler`
    - _Requirements: 6.3, 2.2, 4.2, 5.2_
  - [ ] 3.2 Implement InvalidCustomerIdException and handler
    - Write test: when `InvalidCustomerIdException` is thrown, response is 400 with Error_Response containing "Bad Request"
    - Create `InvalidCustomerIdException` class and handler method
    - _Requirements: 6.2, 2.3, 4.4, 5.3_
  - [ ] 3.3 Implement MethodArgumentNotValidException handler (validation errors)
    - Write test: when validation fails on multiple fields, response is 400 with message listing all invalid fields
    - Implement handler that iterates `FieldError` instances and concatenates messages
    - _Requirements: 6.2, 10.8_
  - [ ] 3.4 Implement HttpMessageNotReadableException handler (malformed JSON)
    - Write test: when request body is malformed JSON, response is 400 with message "Request body is malformed"
    - Implement handler method
    - _Requirements: 3.5, 6.2_
  - [ ] 3.5 Implement HttpMediaTypeNotSupportedException handler
    - Write test: when Content-Type is not application/json, response is 415 with Error_Response
    - Implement handler method
    - _Requirements: 11.3_
  - [ ] 3.6 Implement HttpMediaTypeNotAcceptableException handler
    - Write test: when Accept header excludes application/json and `*/*`, response is 406
    - Implement handler method
    - _Requirements: 11.4_
  - [ ] 3.7 Implement catch-all Exception handler
    - Write test: when unexpected exception occurs, response is 500 with "Internal Server Error" and generic message
    - Implement catch-all `@ExceptionHandler(Exception.class)` method
    - _Requirements: 6.4_
  - [ ] 3.8 Verify all error responses include all five fields with non-null values
    - Write test asserting timestamp is ISO 8601 UTC format and path matches request URI across all handler methods
    - _Requirements: 6.1, 6.5_
  - [ ]* 3.9 Write property test for error response structure
    - **Property 7: Error responses always contain all required fields**
    - **Validates: Requirements 6.1, 6.5**

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement CustomerService (TDD)
  - [ ] 5.1 Implement listCustomers with hardcoded stub data
    - Write test: `listCustomers(0, 20)` returns list of two customers (cust-001 Jane Smith, cust-002 John Doe) with all fields populated
    - Implement service with hardcoded customer map
    - _Requirements: 1.1_
  - [ ] 5.2 Implement getCustomer for known and unknown IDs
    - Write test: `getCustomer("cust-001")` returns Jane Smith's data
    - Write test: `getCustomer("unknown-id")` throws `CustomerNotFoundException`
    - Implement lookup logic
    - _Requirements: 2.1, 2.2_
  - [ ] 5.3 Implement createCustomer with ID generation
    - Write test: `createCustomer(validRequest)` returns Customer with id starting with "cust-" and all submitted fields echoed
    - Implement ID generation (`cust-` + UUID fragment)
    - _Requirements: 3.1_
  - [ ] 5.4 Implement updateCustomer for known and unknown IDs
    - Write test: `updateCustomer("cust-001", validRequest)` returns Customer with id "cust-001" and updated fields
    - Write test: `updateCustomer("unknown-id", request)` throws `CustomerNotFoundException`
    - _Requirements: 4.1, 4.2_
  - [ ] 5.5 Implement deleteCustomer for known and unknown IDs
    - Write test: `deleteCustomer("cust-001")` completes without exception
    - Write test: `deleteCustomer("unknown-id")` throws `CustomerNotFoundException`
    - _Requirements: 5.1, 5.2_

- [ ] 6. Implement CustomerController (TDD)
  - [ ] 6.1 Implement GET /customers endpoint with pagination parameters
    - Write MockMvc test: GET `/customers` returns 200 with JSON array of two customers
    - Write MockMvc test: GET `/customers?page=0&size=20` returns 200
    - Implement `@GetMapping` with `@RequestParam` for page and size
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ] 6.2 Implement pagination parameter validation
    - Write MockMvc test: GET `/customers?size=0` returns 400 with Error_Response
    - Write MockMvc test: GET `/customers?size=101` returns 400 with Error_Response
    - Write MockMvc test: GET `/customers?page=-1` returns 400 with Error_Response
    - Write MockMvc test: GET `/customers?page=abc` returns 400 with Error_Response
    - Implement validation via `@Min`/`@Max` constraints or manual validation
    - _Requirements: 1.4, 1.5, 1.6_
  - [ ] 6.3 Implement GET /customers/{customerId} with ID format validation
    - Write MockMvc test: GET `/customers/cust-001` returns 200 with Jane Smith data
    - Write MockMvc test: GET `/customers/invalid@id` returns 400 with Error_Response
    - Implement path variable validation using regex pattern `^[a-zA-Z0-9\\-]+$`
    - _Requirements: 2.1, 2.3_
  - [ ] 6.4 Implement POST /customers endpoint
    - Write MockMvc test: POST `/customers` with valid body returns 201 with generated id
    - Write MockMvc test: POST `/customers` with missing firstName returns 400
    - Write MockMvc test: POST `/customers` with invalid email returns 400
    - Implement `@PostMapping` with `@Valid @RequestBody CustomerCreate`
    - _Requirements: 3.1, 3.2, 3.4_
  - [ ] 6.5 Implement PUT /customers/{customerId} endpoint
    - Write MockMvc test: PUT `/customers/cust-001` with valid body returns 200
    - Write MockMvc test: PUT `/customers/unknown-id` returns 404
    - Write MockMvc test: PUT `/customers/cust-001` with missing fields returns 400
    - Implement `@PutMapping` with `@Valid @RequestBody` and ID validation
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [ ] 6.6 Implement DELETE /customers/{customerId} endpoint
    - Write MockMvc test: DELETE `/customers/cust-001` returns 204 with no body
    - Write MockMvc test: DELETE `/customers/unknown-id` returns 404
    - Write MockMvc test: DELETE `/customers/invalid@id` returns 400
    - Implement `@DeleteMapping` with ID validation
    - _Requirements: 5.1, 5.2, 5.3_
  - [ ] 6.7 Implement content-type handling
    - Write MockMvc test: POST with Content-Type `text/xml` returns 415
    - Write MockMvc test: GET with Accept `text/xml` (excluding `application/json` and `*/*`) returns 406
    - Write MockMvc test: response bodies have Content-Type `application/json`
    - Ensure `produces = "application/json"` and `consumes = "application/json"` on relevant endpoints
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  - [ ]* 6.8 Write property tests for pagination validation
    - **Property 1: Invalid pagination range returns 400**
    - **Property 2: Non-integer pagination parameter returns 400**
    - **Validates: Requirements 1.4, 1.5, 1.6**
  - [ ]* 6.9 Write property tests for customer ID validation
    - **Property 3: Unknown valid-format customer ID returns 404**
    - **Property 4: Invalid-format customer ID returns 400**
    - **Validates: Requirements 2.2, 2.3, 4.2, 4.4, 5.2, 5.3**
  - [ ]* 6.10 Write property tests for customer creation
    - **Property 5: Valid customer creation echoes all fields**
    - **Property 6: Invalid email format returns 400**
    - **Validates: Requirements 3.1, 3.4, 10.3**
  - [ ]* 6.11 Write property tests for validation
    - **Property 11: Blank required field produces 400**
    - **Property 12: Multiple validation failures reported together**
    - **Validates: Requirements 10.1, 10.2, 10.5, 10.6, 10.7, 10.8**
  - [ ]* 6.12 Write property tests for content-type handling
    - **Property 13: Responses with body have JSON Content-Type**
    - **Property 14: Unsupported Content-Type returns 415**
    - **Property 15: Non-acceptable Accept header returns 406**
    - **Validates: Requirements 11.1, 11.3, 11.4**

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement AddressServiceClient (TDD)
  - [ ] 8.1 Implement ClientConfig with WebClient beans
    - Write test: Spring context loads with WebClient beans configured for address and item service base URLs
    - Implement `ClientConfig` with `@Configuration` and `@Bean` methods reading from `client.address-service.base-url` and `client.item-service.base-url`
    - _Requirements: 7.1, 8.1_
  - [ ] 8.2 Implement AddressServiceClient CRUD methods
    - Write MockWebServer test: `listAddresses(0, 20)` sends GET to `/addresses?page=0&size=20` and returns Flux<Address>
    - Write MockWebServer test: `getAddress("addr-001")` sends GET to `/addresses/addr-001` and returns Mono<Address>
    - Write MockWebServer test: `createAddress(body)` sends POST to `/addresses` and returns Mono<Address>
    - Write MockWebServer test: `updateAddress("addr-001", body)` sends PUT to `/addresses/addr-001` and returns Mono<Address>
    - Write MockWebServer test: `deleteAddress("addr-001")` sends DELETE to `/addresses/addr-001` and returns Mono<Void>
    - Implement all methods using injected WebClient
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6_
  - [ ] 8.3 Implement error propagation for AddressServiceClient
    - Write MockWebServer test: when Address Service returns 404, client emits reactive error with status code
    - Write MockWebServer test: when Address Service returns 500, client emits reactive error with status code
    - Implement `.onStatus()` handling in WebClient calls
    - _Requirements: 7.7_
  - [ ]* 8.4 Write property test for Address Service Client error propagation
    - **Property 8: Address Service Client propagates HTTP errors**
    - **Validates: Requirements 7.7**

- [ ] 9. Implement ItemServiceClient (TDD)
  - [ ] 9.1 Implement ItemServiceClient CRUD methods
    - Write MockWebServer test: `listItems(0, 20, null)` sends GET to `/items?page=0&size=20` and returns Flux<Item>
    - Write MockWebServer test: `listItems(0, 20, true)` sends GET to `/items?page=0&size=20&inStock=true`
    - Write MockWebServer test: `getItem("item-001")` sends GET to `/items/item-001` and returns Mono<Item>
    - Write MockWebServer test: `createItem(body)` sends POST to `/items` and returns Mono<Item>
    - Write MockWebServer test: `updateItem("item-001", body)` sends PUT to `/items/item-001` and returns Mono<Item>
    - Write MockWebServer test: `deleteItem("item-001")` sends DELETE to `/items/item-001` and returns Mono<Void>
    - Implement all methods using injected WebClient
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ] 9.2 Implement error propagation for ItemServiceClient
    - Write MockWebServer test: when Item Service returns 4xx/5xx, client emits reactive error with status code
    - Implement `.onStatus()` handling in WebClient calls
    - _Requirements: 8.3_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using jqwik
- Unit tests validate specific examples and edge cases
- All tasks follow strict TDD: write failing test first, then minimal implementation
- The execution order (Models → ExceptionHandler → Service → Controller → Clients) prioritizes components with the most edge cases first
- MockMvc is used for controller integration tests; MockWebServer for client tests

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.5", "2.6"] },
    { "id": 2, "tasks": ["2.3", "2.4", "2.7", "2.8"] },
    { "id": 3, "tasks": ["3.1", "3.2", "3.4", "3.5", "3.6", "3.7"] },
    { "id": 4, "tasks": ["3.3", "3.8", "3.9"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5"] },
    { "id": 6, "tasks": ["6.1", "6.2", "6.3"] },
    { "id": 7, "tasks": ["6.4", "6.5", "6.6", "6.7"] },
    { "id": 8, "tasks": ["6.8", "6.9", "6.10", "6.11", "6.12"] },
    { "id": 9, "tasks": ["8.1"] },
    { "id": 10, "tasks": ["8.2", "9.1"] },
    { "id": 11, "tasks": ["8.3", "8.4", "9.2"] }
  ]
}
```
