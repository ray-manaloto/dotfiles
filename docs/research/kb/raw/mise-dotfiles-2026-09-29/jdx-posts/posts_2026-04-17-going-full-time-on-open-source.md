[Skip to content](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/#main)

On this page

For the last several years, I’ve been building and maintaining developer tools in my spare time, chiefly [mise](https://mise.jdx.dev/).

What started as a simple rewrite of [asdf](https://asdf-vm.com/) in Rust has become an incredibly successful local dev manager. mise now has [27k+ stars on GitHub](https://github.com/jdx/mise) and is the [10th most downloaded Homebrew formula](https://formulae.brew.sh/analytics/install-on-request/30d/). In fact, roughly 1% of users typing `brew install` are running `brew install mise`.

I’ve also watched mise show up in places I never expected, including [OpenAI Codex Universal](https://github.com/openai/codex-universal/blob/54b8f0434886aeff0817cc4d5a7d76bdb0d834d5/Dockerfile#L86-L100) and [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell/blob/e4d6f92d9b803719928eca5187b428a7ca55c1a5/mise.toml).

Alongside it I maintain [aube](https://github.com/endevco/aube) (the newest of the bunch, which I’m really excited about), [hk](https://hk.jdx.dev/) (git hook runner), [pitchfork](https://pitchfork.jdx.dev/) (process supervisor), [fnox](https://fnox.jdx.dev/) (secrets), [usage](https://github.com/jdx/usage), and a handful of smaller tools.

That has been incredibly rewarding. It’s also become a lot of work. For a while, I could do this alongside a full-time job. But as mise has grown, that has become less and less realistic. I have not been able to keep up with PR review the way I want to. I’ve had to declare notification bankruptcy every few weeks by deleting all of my GitHub notifications because I genuinely could not keep up.

I do not want mise to stall because I only have scraps of time left after work. I want it to keep getting better.

So I left Figma to work on these full time.

## Update: entire.io [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#update-entireio)

This post originally introduced en.dev as the home for my open source work. The center of gravity has moved to [jdx.dev](https://jdx.dev/): I am now an open source developer for [entire.io](https://entire.io/), where I primarily work on mise, aube, fnox, hk, pitchfork, and my other open source tools. Entire is the title sponsor of that work.

The old en.dev URLs are being kept around for compatibility, but sponsorships, memberships, and project updates now live on [jdx.dev/sponsors.html](https://jdx.dev/sponsors).

## Money [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#money)

My OSS work does not currently make enough money for me to live on. Right now, I make roughly:

- **$100/month** from ads in the docs
- **$500/month** from GitHub Sponsors

I’m grateful for this, but it won’t be enough, so I am going to try a few different ways to make this work.

### Memberships [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#memberships)

For individuals who want to support the work, I’ve set up tiered memberships at [jdx.dev](https://jdx.dev/sponsors):

- **Supporter** — $5/mo or $50/yr
- **Member** — $10/mo or $100/yr
- **Sustaining Member** — $20/mo or $200/yr
- **Patron** — $50+/mo or $500+/yr

Members get access to a monthly newsletter. Higher tiers add a members-only Discord, a monthly Live Q&A, and a mention in `mise patrons`.

### Sponsorships [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#sponsorships)

For companies that rely on mise, I’m offering two sponsor tiers:

- **Backer** — logo on [jdx.dev](https://jdx.dev/sponsors), plus sponsor visibility for small teams that depend on mise.
- **Partner / Premier** — logo on [jdx.dev](https://jdx.dev/sponsors), docs placement, and more prominent acknowledgement across the tools.

Sponsorship is not roadmap control, and it is not a private support contract. It is a way for companies to fund the open source infrastructure they depend on.

### Consulting [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#consulting)

I’m also going to spend up to 2 days a week consulting for companies that want hands-on help adopting mise. Typical engagements look like:

- Migrating a monorepo’s tooling onto `mise.toml`
- Wiring mise into CI and standardising images / containers
- Authoring custom plugins for internal tools
- Reviewing how secrets and env vars flow through developer machines

Rates are high — I’m the only person in the world who can offer this, slots are scarce, and a portion of every engagement subsidises ongoing mise development.

### Paid Services [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#paid-services)

Longer term, I want to identify paid services I could host for teams that use mise.

I have not figured out exactly what those should be yet. I want these to be simple since my goal is sustainability so that I can build OSS tools, not building a SaaS and becoming a billionaire. If you use mise at work and have ideas for services your team would pay for, please let me know.

## The Goal [\#](https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/\#the-goal)

If you use mise and want to support that, you can become a member or sponsor at [jdx.dev](https://jdx.dev/sponsors), or [reach out](https://jdx.dev/contact/) if your company is interested in sponsorship or consulting.

Thank you to everyone who has used mise, contributed to it, reported bugs, written docs, recommended it to a teammate, or sponsored the work already.

> **Update, June 2026:** I am now working as an open source developer at [entire.io](https://entire.io/), where my primary job is continuing to build mise, aube, fnox, hk, pitchfork, and my other open source tools. Sponsorships and memberships now live at [jdx.dev/sponsors.html](https://jdx.dev/sponsors).