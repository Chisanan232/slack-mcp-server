### 🍀 Improvements

1. Migrate the backend component abstraction as a single Python library [abstract-backend] ([GitHub]).
2. Improve the secret info loading mechanism to be more flexible and human. ([PR#214])

[GitHub]: https://github.com/Chisanan232/abstract-backend
[abstract-backend]: https://pypi.org/project/abstract-backend/
[PR#214]: https://github.com/Chisanan232/slack-mcp-server/pull/214


### 🧑‍💻 Developer

1. Change the GitHub Action to reuse the reusable workflows from the [python project reusable GitHub Action] project to 
centralized manage the common usages of CI/CD part.
2. Improve the CI/CD workflows which are relative with documentation to reuse common reusabele workflows. ([PR#222])

[python project reusable GitHub Action]: https://github.com/Chisanan232/GitHub-Action_Reusable_Workflows-Python
[PR#222]: https://github.com/Chisanan232/slack-mcp-server/pull/222


### 📑 Docs

1. Update all the content about the naming usages in [documentation].
2. Update all the content about the CI/CD usages.

[documentation]: https://chisanan232.github.io/abe-redis/


### 🤖 Upgrade dependencies

1. Upgrade the Python dependencies.
2. Upgrade pre-commit dependencies.
3. Upgrade the CI reusable workflows.
