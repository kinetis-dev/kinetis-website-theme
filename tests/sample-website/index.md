---
kinetis_template: landing
og:description: "A complete PHP framework built for persistent workers and non-blocking I/O, covering routing, validation, queues, MCP, and more."
og:image:width: "1200"
og:image:height: "630"
myst:
  html_meta:
    description: "Kinetis is a complete PHP framework built for persistent workers and non-blocking I/O, with a native MCP server and 20+ first-party packages."
    twitter:card: "summary_large_image"
    twitter:title: "Kinetis: A Complete PHP Framework, Built for Speed"
    twitter:description: "A complete PHP framework built for persistent workers and non-blocking I/O, covering routing, validation, queues, MCP, and more."
    twitter:image: "https://kinetis.dev/assets/og-image.png"
---

```{title} Kinetis: A Complete PHP Framework, Built for Speed
```

```{toctree}
:hidden:

blog/index
```

```{raw} html
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "Kinetis",
        "description": "A complete PHP framework with a non-blocking core: persistent-worker architecture, Fiber-based concurrency, a native MCP server, and 20+ first-party packages.",
        "url": "https://kinetis.dev/",
        "codeRepository": "https://github.com/kinetis-dev/kinetis",
        "programmingLanguage": "PHP",
        "license": "https://opensource.org/licenses/MIT",
        "runtimePlatform": ["FrankenPHP", "RoadRunner"]
    }
    </script>
    <div class="wrap">
        <header class="hero">
            <div class="logo" role="img" aria-label="Kinetis"></div>
            <p class="eyebrow">Persistent Workers, Non-Blocking I/O</p>
            <h1 class="visually-hidden">Kinetis</h1>
            <p class="tagline">
                A PHP framework built for persistent workers and non-blocking
                I/O, so your application stays fast under real load and no
                slow request ever ties up the whole process.
            </p>
        </header>

        <div class="tiles">
            <a class="tile" href="/docs/">
                <h2>Documentation <span class="arrow">&rarr;</span></h2>
                <p>Guides, API reference, and configuration, including FrankenPHP and RoadRunner worker modes, and Fiber-based concurrency.</p>
            </a>
            <a class="tile" href="/docs/tutorial.html">
                <h2>Get Started <span class="arrow">&rarr;</span></h2>
                <p>Install Kinetis, get a route running in minutes, then build a real application on it: database, queue, scheduled command, live updates.</p>
            </a>
            <a class="tile" href="https://github.com/kinetis-dev/">
                <h2>Source on GitHub <span class="arrow">&rarr;</span></h2>
                <p>MIT licensed. Every package, every release, in the open.</p>
            </a>
            <a class="tile" href="/docs/benchmarks.html">
                <h2>Benchmarks <span class="arrow">&rarr;</span></h2>
                <p>An auditable, cross-framework benchmark suite, methodology included.</p>
            </a>
        </div>

        <section class="features">
            <h2>Everything your application needs, out of the box</h2>
            <div class="feature-grid">
                <a class="feature" href="/docs/routing-validation.html">
                    <h3>Typed requests, zero boilerplate</h3>
                    <p>Define a route with a PHP attribute. A malformed request comes back a <code>422</code> with every field error at once, before your controller code ever runs.</p>
                </a>
                <a class="feature" href="/docs/routing-validation.html#openapi-documentation">
                    <h3>OpenAPI that's never out of date</h3>
                    <p>A full OpenAPI 3.1 spec and Swagger UI, generated straight from your route attributes. Nothing to hand-write, nothing to fall out of sync.</p>
                </a>
                <a class="feature" href="/docs/concurrency.html">
                    <h3>Real concurrency, not an illusion</h3>
                    <p>Run several database queries, an HTTP call, and a cache read side by side and wait once, all on plain PHP Fibers with no extra processes.</p>
                </a>
                <a class="feature" href="/docs/appendix-runtime.html#the-suspend-resume-pattern">
                    <h3>Non-blocking, top to bottom</h3>
                    <p>A slow database query or a flaky third-party API suspends a Fiber, not the whole worker, so one slow request never stalls the ones behind it.</p>
                </a>
                <a class="feature" href="/docs/mcp.html">
                    <h3>A native AI agent interface</h3>
                    <p>A Model Context Protocol server ships with the framework. Install it, and your API's tools and resources are callable by any MCP-compatible agent.</p>
                </a>
                <a class="feature" href="/docs/auth.html">
                    <h3>Authentication and authorization included</h3>
                    <p>Bearer tokens or JWT, password hashing and token revocation, an unopinionated authorization layer, plus sessions, CSRF, and rate limiting.</p>
                </a>
                <a class="feature" href="/docs/queue.html">
                    <h3>Background jobs, any backend</h3>
                    <p>Queues on Redis, SQL, Amazon SQS, or RabbitMQ, with retries, delays, priorities, and graceful shutdown behind one interface.</p>
                </a>
                <a class="feature" href="/docs/storage.html">
                    <h3>Storage, mail, and search</h3>
                    <p>File storage on local disk or S3, transactional email, and OpenSearch, all built on the same non-blocking core as everything else.</p>
                </a>
                <a class="feature" href="/docs/runtime-adapters.html">
                    <h3>Deploy anywhere, same code</h3>
                    <p>Runs unchanged on classic PHP-FPM, a FrankenPHP or RoadRunner persistent worker, or AWS Lambda. Start simple, move to a worker when it suits you.</p>
                </a>
            </div>
        </section>
    </div>
```
