Create a few sample openapi specifications, complete with examples, common error codes, for a CRESTful API, with POST, PUT, GET and DELETE methods for common CRUD operations, using the usual conventions. Place these files in a folder 'sample-specs'.

Do once for each of the following domain resources:

Customer Service
- id (string, path-variable friendly)
- firstName (string)
- lastName (string)
- title (string)
- phone (string)
- email (string)
- address (Address object - see Address Service below)

Address Service
- id (string, path-variable friendly)
- nameOrNumber (string)
- street (string)
- line1 (string, nullable)
- line2 (string, nullable)
- town (string)
- postCodeOrZip (string)
- country (string)

Item Service
- id (string, path-variable friendly)
- name (string)
- description (string)
- options (string)
- unitPrice (decimal)
- inStock (boolean)
