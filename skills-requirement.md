I want to create a skills file that meets the open agentskills.io format, to be executed when instructed to generate a RESTful microservice using java springboot and maven, for a given swagger server specification.

The skills should direct the code generator to use openapigenerate, rather than manually creating controllers, value objects and other boilerplate. The openapigenerate plugin should use the delegate pattern, whereby code is generated on demand.

The sample-pom.xml file illustratesthe other settings for the openapigenerate maven plugin to use - see lines 107-134.

Optionally, the skill should support generation of http clients for downstream microservices - see lines 136-156 of the sample pom. This execution block would be repeated once for each downstream microservice supported in this way.

The sample pom file follows a convention of a top-level folder 'spec', with subfolders 'server' and 'client' holding the OpenApi specs against which the code will be generated.

The sample pom is an otherwise minimal file with springboot web and lombok added, and uses the latest version of the openapigenerate plugin at time of writing. The skill should be able to work with any existing springboot app.
