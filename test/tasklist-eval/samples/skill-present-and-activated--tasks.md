# Tasks: Customer Service API

## Task 1: Create feature branch
- [x] Create and check out a feature branch `feat/customer-service-api` from the current base branch

## Task 2: Configure openapi-generator and dependencies in pom.xml
- [x] Add required dependencies to `pom.xml`: `jackson-databind-nullable`, `spring-boot-starter-webflux`, `jakarta.validation-api`, `swagger-annotations`
- [x] Add `openapi-generator-maven-plugin` with three executions: `CustomerApiServer` (server delegate), `AddressApiWebClient` (webclient), `ItemApiWebClient` (webclient)
- [x] Add `build-helper-maven-plugin` to register client generated-source directories as compile source roots
- [x] Run `mvn clean compile` to verify code generation succeeds and the project compiles
- [x] Commit: `build: configure openapi-generator for server and client code generation`

## Task 3: Implement listCustomers — Red-Green-Refactor cycle
- [x] Read the generated `CustomersApiDelegate` interface from `target/generated-sources` to confirm exact method signatures
- [x] Write a failing test: `CustomersApiDelegateImplTest.listCustomers_returnsHardcodedCustomers` — asserts the delegate returns a list of two customers with the expected names and IDs
- [x] Confirm the test fails (Red)
- [x] Implement `CustomersApiDelegateImpl.listCustomers` with minimum code to pass the test
- [x] Confirm all tests pass (Green)
- [x] Refactor if needed
- [x] Commit: `feat: listCustomers returns hardcoded customer list`

## Task 4: Implement getCustomerById — Red-Green-Refactor cycle
- [x] Write a failing test: `getCustomerById_returnsHardcodedCustomer` — asserts the delegate returns Jane Smith (cust-001)
- [x] Confirm the test fails (Red)
- [x] Implement `getCustomerById` with minimum code to pass the test
- [x] Confirm all tests pass (Green)
- [x] Refactor if needed
- [x] Commit: `feat: getCustomerById returns hardcoded customer`

## Task 5: Implement createCustomer — Red-Green-Refactor cycle
- [x] Write a failing test: `createCustomer_returnsCreatedCustomerWith201` — asserts the delegate returns a customer with id "cust-003" and HTTP 201
- [x] Confirm the test fails (Red)
- [x] Implement `createCustomer` with minimum code to pass the test
- [x] Confirm all tests pass (Green)
- [x] Refactor if needed
- [x] Commit: `feat: createCustomer returns hardcoded customer with 201`

## Task 6: Implement updateCustomer — Red-Green-Refactor cycle
- [x] Write a failing test: `updateCustomer_returnsUpdatedCustomer` — asserts the delegate returns updated customer data
- [x] Confirm the test fails (Red)
- [x] Implement `updateCustomer` with minimum code to pass the test
- [x] Confirm all tests pass (Green)
- [x] Refactor if needed
- [x] Commit: `feat: updateCustomer returns hardcoded updated customer`

## Task 7: Implement deleteCustomer — Red-Green-Refactor cycle
- [x] Write a failing test: `deleteCustomer_returns204` — asserts the delegate returns HTTP 204 with no body
- [x] Confirm the test fails (Red)
- [x] Implement `deleteCustomer` with minimum code to pass the test
- [x] Confirm all tests pass (Green)
- [x] Refactor if needed
- [x] Commit: `feat: deleteCustomer returns 204 no content`

## Task 8: Final verification
- [x] Run `mvn clean test` to confirm the full build and all tests pass end-to-end