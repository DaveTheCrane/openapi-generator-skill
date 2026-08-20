# Springboot Openapi Generator skill

This repo contains a skill in the standard agentskills.io format that will guide a code generating LLM working on a Springboot project with maven to use the [openapi-generator maven plugin](https://openapi-generator.tech/docs/generators/spring/) when creatimg code based on a rest interface, rather than manually generating controllers, request and response objects.

Specifically, it follows a set of conventions for that plugin that will put the majority of code generated into the generated-sources folder, with an ApiDelegate committed into src/main/java, to which business logic can be attached.

The skill has been tuned to proide guidance on how to navigate the maven code generation phase, as early attempts of using the skill tended to run into problems.

## Advantages to this approach

- less code committed into the repo, requiring unit test coverage and other maintenance.
- cheaper token cost for delivery of the same value
- more consustent output, as the generated code follows a templated pattern. If you need to build 20 microservices from swagger, then this way they'll all look the same, whereas manually-generated LLM code will vary.