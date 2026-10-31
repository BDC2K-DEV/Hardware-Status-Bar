# Contributing

Keep runtime changes in `extension/`; never edit generated ZIPs. Run the README checks and test UI changes in a disposable GNOME session. Never test Kill against a user's working app. New GNOME versions and desktop environments need actual runtime testing before adding compatibility claims.

For bugs, include distro, GNOME version, extension release, expected and actual behavior, and sanitized extension errors. Do not include private window titles, documents, command lines, tokens, or full process dumps. Keep changes scoped and update the changelog and compatibility table when behavior changes.
