# Security Policy

## Supported versions

Security fixes are applied to the latest release and the `main` branch.

## Reporting a vulnerability

Do not publish archive traversal, command execution, overwrite, data-loss, or packaging vulnerabilities in a public issue before a fix is available. Use GitHub's private vulnerability reporting feature for this repository.

Include the affected version, operating system, source and target formats, reproduction steps, and a minimal non-sensitive sample when possible.

## Security design

- External media conversion uses `subprocess.run` with `shell=False`.
- Destination data is generated in a same-directory temporary file and atomically moved into place.
- The source is recycled only after a successful destination commit.
- ZIP and TAR repacking rejects path traversal, links, device files, excessive entry counts, excessive expansion size, and suspicious ZIP compression ratios.
- Existing outputs require explicit overwrite authorization.
