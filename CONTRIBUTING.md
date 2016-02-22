# Contributing to PlexPy

## Issues
In case you read this because you are posting an issue, please take a minute and conside the things below. The issue tracker is not a support forum. It is primarily intended to submit bugs, improvements or feature requests. However, we are glad to help you, and make sure the problem is not caused by PlexPy, but don't expect step-by-step answers.

##### Many issues can simply be solved by:

- Making sure you update to the latest version. 
- Turning your device off and on again.
- Analyzing your logs, you just might find the solution yourself!
- Using the **search** function to see if this issue has already been reported/solved.
- Checking the [Wiki](https://github.com/drzoidberg33/plexpy/wiki) for 
[ [Installation] ](https://github.com/drzoidberg33/plexpy/wiki/Installation) and 
[ [FAQs] ](https://github.com/drzoidberg33/plexpy/wiki/Frequently-Asked-Questions-(FAQ)).
- For basic questions try asking on [Gitter](https://gitter.im/drzoidberg33/plexpy) or the [Plex Forums](https://forums.plex.tv/discussion/169591/plexpy-another-plex-monitoring-program) first before opening an issue.

##### If nothing has worked:

1. Open a new issue on the GitHub [issue tracker](http://github.com/drzoidberg33/plexpy/issues).
2. Provide a clear title to easily help identify your problem.
3. Use proper [markdown syntax](https://help.github.com/articles/github-flavored-markdown) to structure your post (i.e. code/log in code blocks).
4. Make sure you provide the following information:
    - [ ] Version
    - [ ] Branch
    - [ ] Commit hash
    - [ ] Operating system
    - [ ] Python version
    - [ ] What you did?
    - [ ] What happened?
    - [ ] What you expected?
    - [ ] How can we reproduce your issue?
    - [ ] What are your (relevant) settings?
    - [ ] Include a link to your **FULL** (not just a few lines!) log file that has the error. Please use [Gist](http://gist.github.com) or [Pastebin](http://pastebin.com/).
5. Close your issue when it's solved! If you found the solution yourself please comment so that others benefit from it.

## Feature Requests

1. Search for similar existing 'issues', feature requests can be recognized by the blue `enhancement` label.
2. If a similar request exists, post a comment (+1, or add a new idea to the existing request).
3. If no similar requests exist, you can create a new one.
4. Provide a clear title to easily identify the feature request.
5. Tag your feature request with `[Feature Request]` so it can be identified easily.

## Pull Requests
If you think you can contribute code to the PlexPy repository, do not hesitate to submit a pull request.

### Branches
All pull requests should be based on the `dev` branch, to minimize cross merges. When you want to develop a new feature, clone the repository with `git clone origin/dev -b FEATURE_NAME`. Use meaningful commit messages.

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