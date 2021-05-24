# 3rd Party APIs Guide

## 3rd Party APIs:

* [Imgur](3rd-party-apis-guide.md#imgur)
* [Cloudinary](3rd-party-apis-guide.md#cloudinary)
* [MaxMind](3rd-party-apis-guide.md#maxmind)

## [Imgur](3rd-party-apis-guide.md) <a id="imgur"></a>

1. Sign up for an [Imgur account](https://imgur.com/register). Make sure to verify the account.
2. Register a [new application](https://api.imgur.com/oauth2/addclient).
3. Enter an **Application Name**, **Email**, **Description**, and select the option "_OAuth 2 authorization without a callback URL_", then click "_Submit_".
4. Copy the **Client ID** and fill in the Tautulli setting.

## [Cloudinary](3rd-party-apis-guide.md) <a id="cloudinary"></a>

1. Sign up for a [Cloudinary account](https://cloudinary.com/users/register/free). Make sure to verify the account.
2. From the Cloudinary dashboard, copy the **Cloud Name**, **API Key**, and **API Secret** and fill in the Tautulli settings.

## [MaxMind](3rd-party-apis-guide.md) <a id="MaxMind"></a>

Note: The GeoLite2 database is not required for Tautulli v2.2.3 and above. Geolocation lookup is done via Plex.tv.

Legacy instructions for pre-v2.2.3 1. Sign up for a \[MaxMind account\]\(https://www.maxmind.com/en/geolite2/signup\). Make sure to verify the account. 1. Go to your \*Account\*, then \*Services\* &gt; \*My License Key\* in the side menu, then click "\*Generate New License Key\*". 1. Enter a \*\*License key description\*\*, and select "\*No\*" for "\*Will this key be used for GeoIP Update?\*", then click "\*Confirm\*". 1. Copy the \*License Key\* and fill in the Tautulli setting.

