from twitter import Api, TwitterError
import requests


class Api(Api):
    def DebugEndpoint(self, verb=None, endpoint=None, data=None):
        """ Request a url and return raw data. For testing purposes only.

        Args:
            url:
                The web location we want to retrieve.
            verb:
                Either POST or GET.
            data:
                A dict of (str, unicode) key/value pairs.

        Returns:
            data
        """

        url = "{0}{1}".format(self.base_url, endpoint)

        if verb == 'POST':
            if 'media_ids' in data:
                url = self._BuildUrl(
                    url,
                    extra_params={
                        'media_ids': data['media_ids']
                    }
                )
                print('POSTing url:', url)
            if 'media' in data:
                try:
                    print('POSTing url:', url)
                    raw_data = requests.post(
                        url,
                        files=data,
                        auth=self.__auth,
                        timeout=self._timeout
                    )
                except requests.RequestException as e:
                    raise TwitterError(str(e))
            else:
                try:
                    print('POSTing url:', url)
                    raw_data = requests.post(
                        url,
                        data=data,
                        auth=self.__auth,
                        timeout=self._timeout
                    )
                except requests.RequestException as e:
                    raise TwitterError(str(e))
        if verb == 'GET':
            url = self._BuildUrl(url, extra_params=data)
            print('GETting url:', url)
            try:
                raw_data = requests.get(
                    url,
                    auth=self.__auth,
                    timeout=self._timeout)

            except requests.RequestException as e:
                raise TwitterError(str(e))
        return raw_data._content
