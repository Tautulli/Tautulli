### 3rd Party APIs:

* [Imgur](#imgur)
* [Cloudinary](#cloudinary)
* [MaxMind](#maxmind)

---

### <a id="imgur">Imgur</a>

1. Sign up for an [Imgur account](https://imgur.com/register). Make sure to verify the account.
1. Register a [new application](https://api.imgur.com/oauth2/addclient).
1. Enter an **Application Name**, **Email**, **Description**, and select the option "*OAuth 2 authorization without a callback URL*", then click "*Submit*".
1. Copy the **Client ID** and fill in the Tautulli setting.

---

### <a id="cloudinary">Cloudinary</a>

1. Sign up for a [Cloudinary account](https://cloudinary.com/users/register/free). Make sure to verify the account.
1. From the Cloudinary dashboard, copy the **Cloud Name**, **API Key**, and **API Secret** and fill in the Tautulli settings.

---

### <a id="MaxMind">MaxMind</a>

Note: The GeoLite2 database is not required for Tautulli v2.2.3 and above. Geolocation lookup is done via Plex.tv.

<details>
<summary>Legacy instructions for pre-v2.2.3</summary>

1. Sign up for a [MaxMind account](https://www.maxmind.com/en/geolite2/signup). Make sure to verify the account.
1. Go to your *Account*, then *Services* > *My License Key* in the side menu, then click "*Generate New License Key*".
1. Enter a **License key description**, and select "*No*" for "*Will this key be used for GeoIP Update?*", then click "*Confirm*".
1. Copy the *License Key* and fill in the Tautulli setting.

</details>