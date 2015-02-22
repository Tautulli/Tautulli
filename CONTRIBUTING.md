# Contributing to PlexPy

## Issues
In case you read this because you are posting an issue, please take a minute and conside the things below. The issue tracker is not a support forum. It is primarily intended to submit bugs, improvements or feature requests. However, we are glad to help you, and make sure the problem is not caused by PlexPy, but don't expect step-by-step answers.

* Use the search function. Chances are that your problem is already discussed. Do not append to (closed) issues if your problem does not fit the discussion.
* Visit the [Troubleshooting](../../wiki/TroubleShooting) wiki first.
* Use [proper formatting](https://help.github.com/articles/github-flavored-markdown/). Paste your logs in code blocks.
* Close your issue if you resolved it.

## Pull Requests
If you think you can contribute code to the PlexPy repository, do not hesitate to submit a pull request.

### Branches
All pull requests should be based on the `develop` branch, to minimize cross merges. When you want to develop a new feature, clone the repository with `git clone origin/develop -b FEATURE_NAME`. Use meaningful commit messages.

### Python Code

#### Compatibility
The code should work with Python 2.6 and 2.7. Note that PlexPy runs on different platforms, including Network Attached Storage devices such as Synology.

Re-use existing code. Do not hesitate to add logging in your code. You can the logger module `plexpy.logger.*` for this. Web requests are invoked via `plexpy.request.*` and derived ones. Use these methods to automatically add proper and meaningful error handling.

#### Code conventions
Although PlexPy did not adapt a code convention in the past, we try to follow the [PEP8](http://legacy.python.org/dev/peps/pep-0008/) conventions for future code. A short summary to remind you (copied from http://wiki.ros.org/PyStyleGuide):

 * 4 space indentation
 * 80 characters per line
 * `package_name`
 * `ClassName`
 * `method_name`
 * `field_name`
 * `_private_something`
 * `self.__really_private_field`
 * `_global`

#### Documentation
Document your code. Use docstrings See [PEP-257](https://www.python.org/dev/peps/pep-0257/) for more information.

#### Continuous Integration
PlexPy has a configuration file for [travis-ci](https://travis-ci.org/). You can add your forked repo to Travis to have it check your code against PEP8, PyLint, and PyFlakes for you. Your pull request will show a green check mark or a red cross on each tested commit, depending on if linting passes.

### HTML/Template code

#### Compatibility
HTML5 compatible browsers are targetted. There is no specific mobile version of PlexPy yet.

#### Conventions
* 4 space indentation
* `methodName`
* `variableName`
* `ClassName`