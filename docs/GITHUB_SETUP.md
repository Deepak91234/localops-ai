# GitHub and other devices

The public GitHub repository contains the application source, tests, documentation, and dependency lockfiles. The live SQLite database, uploaded business documents, API tokens, `.env`, local dependencies, and recoverable project backups stay on this GX10 and are ignored by Git. The archived demonstration fixtures are included only because the automated tests explicitly use them.

## First upload

Authenticate GitHub on this computer with the GitHub CLI, then create the public repository or choose an existing empty one. A project-local Ubuntu-packaged CLI is available at `.tools/github-cli/usr/bin/gh` when the system does not have `gh`.

```bash
GH_CONFIG_DIR="$PWD/work/github-auth" .tools/github-cli/usr/bin/gh auth login --hostname github.com --git-protocol https --web
GH_CONFIG_DIR="$PWD/work/github-auth" .tools/github-cli/usr/bin/gh auth setup-git
```

This local CLI stores its authorization under ignored `work/github-auth`. On another computer with GitHub CLI installed, use `gh` instead of the project-local executable.

Complete the browser sign-in yourself. Do not paste passwords, access tokens, or recovery codes into chat. The repository must belong to an account or organization you can write to.

For a new public repository named `localops-ai`, once the prepared local commit is ready:

```bash
GH_CONFIG_DIR="$PWD/work/github-auth" .tools/github-cli/usr/bin/gh repo create localops-ai --public --source=. --remote=origin --push
```

For an existing empty repository, use its actual URL:

```bash
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

If it already contains commits, fetch and review its branch history before pushing. Do not force-push over other work.

## Use the code on another device

Clone the repository, then run `./scripts/bootstrap.sh` to install the locked Python/npm dependencies and build the browser application. Set up a supported local Ollama/Nemotron inference endpoint and start with `./scripts/start.sh`. The transient `./scripts/service.sh` launcher requires a Linux systemd user session. Hardware, device telemetry, and the current model are verified on this Ubuntu ARM64 GX10; other hardware may need separate setup.

GitHub stores the source and does not host the running FastAPI application or GX10 inference service. `127.0.0.1` refers to the device where the browser is running. GitHub Pages cannot run this backend. Accessing the running GX10 app from another device requires a separately configured secure network connection and application access controls; the present app deliberately accepts only loopback hosts/origins.

Uploaded knowledge and saved tasks are local runtime state, so they do not synchronize through Git. Back up `work/localops.sqlite3` and `work/knowledge` together through an appropriate private backup process if those records must be transferred.
