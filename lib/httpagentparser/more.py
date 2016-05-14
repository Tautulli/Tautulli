import httpagentparser as hap

class JakartaHTTPClinet(hap.Browser):
    name = 'Jakarta Commons-HttpClient'
    look_for = name
    version_splitters = ['/']

class PythonRequests(hap.Browser):
    name = 'Python Requests'
    look_for = 'python-requests'

# Registering new UAs

hap.detectorshub.register(JakartaHTTPClinet())
hap.detectorshub.register(PythonRequests())

# Tests

if __name__ == '__main__':

    s = 'Jakarta Commons-HttpClient/3.1'

    print(hap.detect(s))
    print(hap.simple_detect(s))

    s = 'python-requests/1.2.3 CPython/2.7.4 Linux/3.8.0-29-generic'

    print(hap.detect(s))
    print(hap.simple_detect(s))
