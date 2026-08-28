# NSQD Command Pitfall

## The `--tcp-address` Trap

In NSQD 1.3.0 (and some earlier versions), passing `--tcp-address=0.0.0.0` or `--http-address=0.0.0.0` in the command causes a misleading error:

```
FATAL: failed to instantiate nsqd - listen (0.0.0.0) failed - listen unix 0.0.0.0: bind: address already in use
```

### What's Actually Happening
NSQD interprets `0.0.0.0` as a Unix socket path rather than a TCP address.
The error message references "unix" because of this misinterpretation.

### The Fix
**Omit the flag entirely.** NSQD defaults to listening on `0.0.0.0:4150` for TCP
and `0.0.0.0:4151` for HTTP. This is the correct default behavior.

### Correct Command
```yaml
# DO THIS:
command: nsqd --data-path=/nsq/data

# DON'T DO THIS:
command: nsqd --tcp-address=0.0.0.0 --http-address=0.0.0.0 --data-path=/nsq/data
```

### When You NEED a Specific Address
If you need to bind to a specific address (e.g., `127.0.0.1`), use the `--tcp-addr`
and `--http-addr` flags (note: **short form with hyphen**, not underscore):

```yaml
command: nsqd --data-path=/nsq/data --tcp-addr=127.0.0.1 --http-addr=127.0.0.1
```