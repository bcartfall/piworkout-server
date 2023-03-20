# TLS / SSL

This folder stores the public and private TLS certificates.

Example:

```bash
openssl req -nodes -new -x509 -keyout key.pem -out cert.pem -days 3650 -subj '/CN=localhost'
```