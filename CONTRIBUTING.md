# Contributing

## Delivery workflow

After the repository baseline, all changes follow:

1. Issue
2. Feature branch
3. Conventional Commit
4. Push
5. Pull request
6. CI and documented review
7. Merge

Direct commits to `main` are not permitted after bootstrap. Pull requests must describe purpose, changes, test evidence, security impact, cost impact, rollback, and remaining risks.

## Repository bootstrap exception

The repository started without any commit or remote default branch, so GitHub had no base reference against which a pull request could be opened. The initial project baseline was therefore committed directly to `main` once. This exception establishes the PR base and does not apply to subsequent work.

## Secrets

Never commit `.env` files, credentials, private keys, access tokens, or local configuration containing secrets. CI/CD credentials must be stored in GitHub Secrets or protected GitHub Environments.
