# Security

## Intended use

FeedApp is meant to run on a **trusted home network**, reached from outside only through a VPN such as Tailscale or WireGuard. It has **no user accounts or authentication**: anyone who can reach its port can read and change all data.

**Do not expose FeedApp directly to the internet.** If you need to, put it behind a reverse proxy that requires a login.

Built-in protections:

- Write requests (`POST`, `PUT`, `PATCH`) must use `Content-Type: application/json`. Browsers then send a CORS preflight, which FeedApp doesn't answer, so other websites can't send writes from a visitor's browser.
- All database queries are parameterised, and all input is validated with Pydantic.
- Static file serving is confined to the built frontend directory.

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Use GitHub's private reporting instead: open the repository's **Security** tab and choose **Report a vulnerability**.

Include what you found, how to reproduce it, and which version or image tag you used. You'll get a reply as soon as possible. This is a hobby project, so please allow a few days.
