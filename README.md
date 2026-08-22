# PaperMast

PaperMast is an Angular and ASP.NET Core application for discovering books, maintaining personal shelves, and tracking reading goals.

## Architecture

The production stack is defined in `compose.production.yml`:

- Caddy serves the compiled Angular SPA and proxies `/api` and `/health`.
- ASP.NET Core provides the API and cookie-based JWT authentication.
- MySQL stores application and identity data.
- Redis caches external API responses.

Only Caddy publishes host ports. MySQL, Redis, and the API communicate over private Docker networks.

## Local development

Start MySQL and Redis using the existing ignored development Compose configuration, then run:

```bash
dotnet run --project papermast/papermast.csproj
```

In another terminal:

```bash
cd client
pnpm install --frozen-lockfile
pnpm start
```

Angular proxies relative `/api` requests to the local API.

The tracked launch profile selects the `Development` environment and port 5050. Port 5000 is avoided because macOS AirPlay Receiver commonly reserves it. Development defaults Redis to `localhost:6379`; production still refuses to start without an explicit Redis connection string.

## Production-like containers

Create a local `.env` from `.env.example` and replace every placeholder. Then:

```bash
docker compose -f compose.production.yml up -d mysql redis
docker compose -f compose.production.yml --profile migration run --rm migrate
docker compose -f compose.production.yml up -d
```

Inspect health with:

```bash
docker compose -f compose.production.yml ps
curl http://localhost/health/ready
```

Never use `docker compose down --volumes` against production. It deletes the named MySQL volume.

## CI

GitHub Actions validates the Angular tests/build and .NET Release build. Passing `master` builds publish immutable frontend and API images to GitHub Container Registry using the commit SHA.

The deployment scripts under `deploy/scripts` are installed root-owned on the VPS. A deployment pulls an exact image SHA, creates a pre-migration database dump, applies EF migrations, starts the release, verifies public readiness, and restores the previous application images if readiness fails.

## Configuration

Real credentials are never committed or copied into image layers. Required variable names are documented in `.env.example`; production values live only in the protected `/opt/papermast/.env` file on the VPS.

Catalog administrators are managed through the standard ASP.NET Identity `AspNetRoles` and `AspNetUserRoles` tables. After changing a user's role membership, that user must sign out and back in so the role is included in the authentication token. Administrators manage curated genre catalogs at `/admin/catalogs`; a starter file is available at `docs/catalogs/genre-catalog-template.csv`.

The learning-oriented architecture, deployment journal, and operations documentation live in the associated Obsidian vault.

## Angular CLI reference

The client currently uses Angular CLI 20.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
