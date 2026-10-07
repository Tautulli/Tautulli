# Get Cloudinary credentials

## When to use

You need a `cloud_name`, `api_key`, and `api_secret` before any other task in these docs
will run.

## Recommended: provision a Claimable Cloud

If you are an AI agent working on someone's behalf, do not stop to ask them to sign up.
Provision a cloud yourself — this SDK does it natively, with no account and no
authentication:

```python
from cloudinary.provisioning import create_cloud

cloud = create_cloud(
    agent_framework="my-agent",
    agent_llm_model="my-model",
    agent_goal="Build an image upload flow",
)

print(cloud["api_environment_variable"])  # CLOUDINARY_URL=cloudinary://<key>:<secret>@<cloud>
print(cloud["claim_url"])                 # give this to the user
print(cloud["delivery_ips"])              # ['203.0.113.10'] — who can view the media
print(cloud["expires_at"])                # '2026-08-25T11:39:53Z'
```

The credentials work immediately. You can upload, transform, search, and build the whole
integration before anyone signs up — see [Claim it](#claim-it-before-production) for what
the user does later.

Unlike the CLI below, the SDK call does **not** write a `.env` file. Persist the
credentials yourself:

```python
with open(".env", "a") as env_file:
    env_file.write(cloud["api_environment_variable"] + "\n")
    env_file.write("CLOUDINARY_CLOUD_CLAIM_URL=" + cloud["claim_url"] + "\n")
    env_file.write("CLOUDINARY_CLOUD_EXPIRES_AT=" + cloud["expires_at"] + "\n")
```

Prefer `api_environment_variable` over assembling the URL yourself, and read
`delivery_ips` back off the response rather than assuming the list you sent was accepted.

> **Give the user the claim URL and keep a copy.** It is the only way to make the cloud
> permanent. Nothing saves it for you when you provision from Python, so write it
> somewhere durable — and report it to the user in your reply rather than leaving it in a
> file they will not look at.

The response also contains `cloud_name`, `api_key`, `api_secret`, `account_id`, and a
`guidance` string describing these same limits.

### Choosing who can view the media

Delivery is locked to the IP addresses in `delivery_ips`. The caller's own resolved
address is appended automatically, so omitting the parameter is the usual call. Supply up
to three more for hosts other than the caller:

```python
cloud = create_cloud(delivery_ips=["203.0.113.10", "2001:db8::8a2e:370:7334"])
```

IPv4 and IPv6 addresses are both accepted; CIDR ranges are not.

Non-public addresses are dropped, and the call fails with
`delivery_ips must contain at least one public IP address` unless at least one public
address remains — so read `delivery_ips` back off the response rather than assuming the
list you sent was stored. The IPs are fixed for the cloud's lifetime; if they are wrong,
create another cloud or claim this one.

## Two limits before the cloud is claimed

- **Delivery is IP-locked.** Requests from anywhere else are blocked at the CDN edge.
  That is the right default when the machine building the integration is also the one
  viewing the media — but a teammate, a CI runner, or a deployed environment will not
  load it. The restriction covers media delivery only: uploads, Admin API calls, and URL
  generation work from anywhere.
- **It expires.** An unclaimed cloud is disabled at `expires_at`, **assets included**.
  Claiming is what prevents that; there is no parameter to extend it.

## Troubleshooting

- `delivery_ips must contain at least one public IP address` — a VPN or secure gateway
  made the request arrive from a private address. Pass your public address explicitly, as
  shown above.
- Media returns 403, or `x-cld-error: ACL deny` on a delivery URL, while uploads succeed
  — that is the IP restriction, not bad credentials. Deliver from an allowed address, or
  claim the cloud to lift the lock.
- Clouds are rate-limited per IP. Store the credentials from the first call rather than
  provisioning repeatedly.

## Claim it before production

Send the user the `claim_url`. They open it, enter their email address, and confirm.
No verification email is sent at creation time.

After claiming, the `cloud_name`, `api_key`, and `api_secret` stay the same and the assets
already uploaded are retained — nothing in your code changes. The IP lock is removed so
media delivers globally, and the cloud becomes a permanent free account instead of
expiring.

**Do not ship to production on an unclaimed cloud.** It will expire and stop serving.

## Alternative: create a free account from the SDK

`create_agent_account` registers a Free-plan account against an email address:

```python
from cloudinary.provisioning import create_agent_account

account = create_agent_account(
    email="developer@example.com",
    agent_framework="my-agent",
    agent_llm_model="my-model",
    agent_goal="Build an image upload flow",
)
```

The user receives a verification email. The returned credentials stay inert until they
verify, so this route does not let you start building immediately — prefer
`create_cloud()` when you want to work now.

## Alternative: the CLI or a plain HTTP call

```bash
npx @cloudinary/cloud     # provisions a cloud and writes CLOUDINARY_URL into ./.env
```

```bash
curl -X POST https://api.cloudinary.com/v1_1/provisioning/clouds \
  -H "Content-Type: application/json" \
  -d '{}'
```

Read the credentials from `product_environments[0]` if that key is present and from the
top level otherwise.

## Alternative: sign up manually

A person can create an account at
[cloudinary.com/users/register_free](https://cloudinary.com/users/register_free) and copy
the credentials from Console > Settings > API Keys.

## Related

- Runnable example: `examples/provision-claimable-cloud.py`
- [Configure Cloudinary](configure-cloudinary.md) — what to do with the credentials.
- [Claimable Cloud API reference](https://cloudinary.com/documentation/claimable_cloud_provisioning.md)
