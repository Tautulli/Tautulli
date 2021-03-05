# Contributing to Tautulli

## Pull Requests
If you think you can contribute code to the Tautulli repository, do not hesitate to submit a pull request.

### Branches
All pull requests should be based on the `nightly` branch, to minimize cross merges. When you want to develop a new feature, clone the repository with `git clone origin/nightly -b FEATURE_NAME`. Use meaningful commit messages.

### Python Code

#### Compatibility
The code should work with Python 3.6+. Note that Tautulli runs on many different platforms.

Re-use existing code. Do not hesitate to add logging in your code. You can the logger module `plexpy.logger.*` for this. Web requests are invoked via `plexpy.request.*` and derived ones. Use these methods to automatically add proper and meaningful error handling.

#### Code conventions
Although Tautulli did not adapt a code convention in the past, we try to follow the [PEP8](http://legacy.python.org/dev/peps/pep-0008/) conventions for future code. A short summary to remind you (copied from http://wiki.ros.org/PyStyleGuide):

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

### HTML/Template code

#### Compatibility
HTML5 compatible browsers are targeted.

#### Conventions
* 4 space indentation
* `methodName`
* `variableName`
* `ClassName`
