# Security Policy

## Supported versions

The project is pre-1.0. Security fixes are applied to `main`; there are no maintained release
branches yet.

## Reporting a vulnerability

Do not open a public issue for a security problem.

Use GitHub's private vulnerability reporting on the repository:

1. Open the **Security** tab.
2. Select **Report a vulnerability**.
3. Include the affected component, reproduction steps, impact, and any suggested fix.

If private reporting is unavailable, contact the maintainers listed in `CODEOWNERS` through a
private channel. Do not include secrets, prompts, or personal data in the report; redact them.

## What to expect

- Acknowledgement within 3 business days, best effort.
- An initial assessment within 7 business days.
- A fix or mitigation plan for confirmed high-severity issues as soon as practical.
- Credit in the advisory if you want it.

This is a volunteer beta project. It does not offer a bug bounty or a paid security program.

## In scope

- Authentication, authorization, session, CSRF, API-key, and worker-token flaws.
- Worker sandbox escape, host access, Docker socket exposure, or GPU isolation failures.
- Points ledger integrity: minting, double-spend, negative balances, or unauthorized grants.
- Inference quota bypass, key leakage, or cross-user data exposure.
- Remote code execution, command injection, SSRF, path traversal, and unsafe deserialization.
- Secrets committed to the repository or leaked in logs.
- Supply-chain issues in build, CI, container, or dependency configuration.

## Out of scope

- Denial of service against your own local deployment.
- Vulnerabilities in third-party services, models, or datasets without a project-specific impact.
- Model quality, hallucinations, or prompt-injection outputs without a platform security boundary
  bypass.
- Social engineering of maintainers.
- Reports that require a compromised host, browser, or already-leaked credentials.

## Safe harbor

We will not pursue legal action for good-faith research that follows this policy, avoids privacy
violations, avoids data destruction, and gives us reasonable time to fix the issue before public
disclosure.

## Secrets

If you accidentally commit a secret, rotate it immediately and tell a maintainer. Removing the file
in a later commit is not enough; assume the value is compromised.
