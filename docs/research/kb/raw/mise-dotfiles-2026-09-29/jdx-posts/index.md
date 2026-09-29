@jdxhttps://jdx.dev/Recent content on @jdxHugoenMon, 14 Sep 2026 10:33:00 -0500Dotfiles That Save Themselveshttps://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/Mon, 07 Sep 2026 00:00:00 +0000https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/<p><code>mise bootstrap</code> already supported two common ways of managing dotfiles: keep them in a repository and symlink them into place, as <a href="https://www.gnu.org/software/stow/" class="external-link" target="\_blank" rel="noopener">GNU Stow</a> does, or generate the live files from stored sources and templates, as <a href="https://www.chezmoi.io/user-guide/frequently-asked-questions/design/#why-doesnt-chezmoi-use-symlinks-like-gnu-stow" class="external-link" target="\_blank" rel="noopener">chezmoi</a> normally does.</p>
<p>I wanted to add a third model: <strong>automatic bidirectional syncing of the files I already edit, without symlinks</strong>. Change <code>.zshrc</code> on my laptop and mise saves it, shares it, and applies it on my desktop. Edit it on the desktop and the change flows back. The live files stay where they are, and I don&rsquo;t have to remember to copy edits back into a source directory or run a sync command after each change.</p>Introducing mr-boxington: fix target/https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/Sat, 05 Sep 2026 00:00:00 +0000https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/<p>I&rsquo;m introducing <a href="https://mr-boxington.jdx.dev" class="external-link" target="\_blank" rel="noopener">mr-boxington</a>, a build cache for Rust that shares compilations across your machine and cleans up after itself. The command is <code>mbx</code>. Set it up once and keep running <code>cargo build</code>, <code>cargo test</code>, and <code>cargo clippy</code> as usual.</p>
<p>The pitch is <strong>fix <code>target/</code></strong>.</p>
<p>If you work on several Rust projects, you probably have a lot of disk space tied up in build outputs. Add git worktrees and you get another copy of those outputs for every branch you&rsquo;re working on. Delete them to reclaim space, and the next build spends time recreating much of the same work.</p>Introducing packsliphttps://jdx.dev/posts/2026-09-05-introducing-packslip/Sat, 05 Sep 2026 00:00:00 +0000https://jdx.dev/posts/2026-09-05-introducing-packslip/<p>I&rsquo;m introducing <a href="https://packslip.dev" class="external-link" target="\_blank" rel="noopener">packslip</a>, a signed manifest vendors publish alongside their releases. It tells package managers which binaries to download, how to verify and install them, and where to find matching shell completions and agent skills.</p>
<p><a href="https://mise.jdx.dev" class="external-link" target="\_blank" rel="noopener">mise</a> supports packslip as a tier 1 backend, preferred over the github and aqua backends for new tools. Completions follow the tool version active in your project, and you can opt in to making that version&rsquo;s skills available to your coding agent.</p>Going Full Time on Open Sourcehttps://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/Thu, 23 Apr 2026 00:00:00 +0000https://jdx.dev/posts/2026-04-17-going-full-time-on-open-source/<p>For the last several years, I&rsquo;ve been building and maintaining developer tools in my spare time, chiefly <a href="https://mise.jdx.dev" class="external-link" target="\_blank" rel="noopener">mise</a>.</p>
<p>What started as a simple rewrite of <a href="https://asdf-vm.com/" class="external-link" target="\_blank" rel="noopener">asdf</a> in Rust has become an incredibly successful local dev manager. mise now has <a href="https://github.com/jdx/mise" class="external-link" target="\_blank" rel="noopener">27k+ stars on GitHub</a> and is the <a href="https://formulae.brew.sh/analytics/install-on-request/30d/" class="external-link" target="\_blank" rel="noopener">10th most downloaded Homebrew formula</a>. In fact, roughly 1% of users typing <code>brew install</code> are running <code>brew install mise</code>.</p>
<p>I&rsquo;ve also watched mise show up in places I never expected, including <a href="https://github.com/openai/codex-universal/blob/54b8f0434886aeff0817cc4d5a7d76bdb0d834d5/Dockerfile#L86-L100" class="external-link" target="\_blank" rel="noopener">OpenAI Codex Universal</a> and <a href="https://github.com/NVIDIA/OpenShell/blob/e4d6f92d9b803719928eca5187b428a7ca55c1a5/mise.toml" class="external-link" target="\_blank" rel="noopener">NVIDIA OpenShell</a>.</p>Contacthttps://jdx.dev/contact/Fri, 17 Apr 2026 00:00:00 +0000https://jdx.dev/contact/<p>For sponsorships, consulting, speaking, or anything else — I read everything that comes through here.</p>

<form class="blog-contact-form" data-contact-form>
 <input type="hidden" name="source" value="contact-page">
 <input type="hidden" name="subject" value="Contact from jdx.dev">
 <p class="contact-field contact-honeypot">
 <label>
 Website
 <input name="website" tabindex="-1" autocomplete="off">
 </label>
 </p>
 <p class="contact-field">
 <label>
 Your name
 <input name="name" required autocomplete="name">
 </label>
 </p>
 <p class="contact-field">
 <label>
 Your email
 <input name="email" type="email" required autocomplete="email">
 </label>
 </p>
 <p class="contact-field">
 <label>
 Your company <span>optional</span>
 <input name="company" autocomplete="organization">
 </label>
 </p>
 <p class="contact-field">
 <label>
 Message
 <textarea name="message" rows="6" required></textarea>
 </label>
 </p>
 <button type="submit">Send message</button>
 <p class="contact-status" data-contact-status aria-live="polite"></p>
</form>

<script>
(function () {
 var forms = document.querySelectorAll('\[data-contact-form\]:not(\[data-contact-ready\])');

 forms.forEach(function (form) {
 form.setAttribute('data-contact-ready', 'true');

 form.addEventListener('submit', async function (event) {
 event.preventDefault();

 var button = form.querySelector('button\[type="submit"\]');
 var status = form.querySelector('\[data-contact-status\]');
 var data = Object.fromEntries(new FormData(form).entries());

 button.disabled = true;
 button.textContent = 'Sending...';
 status.textContent = '';
 status.className = 'contact-status';

 try {
 var res = await fetch('/.netlify/functions/contact', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(data),
 });

 if (!res.ok) throw new Error('Request failed');

 form.reset();
 status.textContent = 'Thanks, I got it.';
 status.className = 'contact-status contact-success';
 } catch (err) {
 status.textContent = 'Something went wrong. Please try again later.';
 status.className = 'contact-status contact-error';
 } finally {
 button.disabled = false;
 button.textContent = 'Send message';
 }
 });
 });
}());
</script>Top 10 Features in Mise You're Not Usinghttps://jdx.dev/posts/2026-03-02-10-mise-features/Mon, 02 Mar 2026 00:00:00 +0000https://jdx.dev/posts/2026-03-02-10-mise-features/<h2 id="1-task-sources-and-outputs">1. Task <code>sources</code> and <code>outputs</code> <a class="heading-anchor" href="#1-task-sources-and-outputs" aria-label="Link to 1. Task sources and outputs">#</a></h2>
<p>Any task can declare input/output globs. If all outputs are newer than all sources, the task is skipped entirely:</p>
<div class="highlight"><pre tabindex="0" style="color:#f8f8f2;background-color:#282a36;-moz-tab-size:4;-o-tab-size:4;tab-size:4;-webkit-text-size-adjust:none;"><code class="language-toml" data-lang="toml"><span style="display:flex;"><span>\[tasks.build\]
</span></span><span style="display:flex;"><span>run = <span style="color:#f1fa8c">&#34;cargo build&#34;</span>
</span></span><span style="display:flex;"><span>sources = \[<span style="color:#f1fa8c">&#34;Cargo.toml&#34;</span>, <span style="color:#f1fa8c">&#34;src/\*\*/\*.rs&#34;</span>\]
</span></span><span style="display:flex;"><span>outputs = \[<span style="color:#f1fa8c">&#34;target/debug/myapp&#34;</span>\]
</span></span></code></pre></div><p>Don&rsquo;t want to enumerate outputs? Set <code>outputs = { auto = true }</code> (which is actually the default when <code>sources</code> is defined) — mise tracks a hash internally and skips the task if sources haven&rsquo;t changed.</p>Shims: How they work in mise-en-placehttps://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/Sat, 13 Apr 2024 01:00:00 +0000https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/<p>Assuming you&rsquo;ve setup <a href="https://mise.jdx.dev" class="external-link" target="\_blank" rel="noopener">mise</a> and have it configured in a couple of
projects to switch between different versions of node, that will happen automatically
when entering the project directories:</p>
<div class="highlight"><pre tabindex="0" style="color:#f8f8f2;background-color:#282a36;-moz-tab-size:4;-o-tab-size:4;tab-size:4;-webkit-text-size-adjust:none;"><code class="language-bash" data-lang="bash"><span style="display:flex;"><span>$ <span style="color:#8be9fd;font-style:italic">cd</span> ~/src/proj1
</span></span><span style="display:flex;"><span>$ node -v
</span></span><span style="display:flex;"><span>20.0.0
</span></span><span style="display:flex;"><span>$ <span style="color:#8be9fd;font-style:italic">cd</span> ~/src/proj2
</span></span><span style="display:flex;"><span>$ node -v
</span></span><span style="display:flex;"><span>18.0.0
</span></span></code></pre></div><p>The way that mise is able to switch this version depends on whether you&rsquo;ve activated
mise with shims or not. In this article, I&rsquo;ll explain how these methods work under the
hood and the pros and cons of using them.</p>Shims: Build a version managerhttps://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/Sat, 13 Apr 2024 00:00:00 +0000https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/<p>I&rsquo;ve spent the last decade of my career in the developer productivity space. In that time
I&rsquo;ve helped countless developers setup their dev environments. Something I see time and
time again are developers struggling with version managers for their programming languages.</p>
<p>These tools are generally fine, but developers often don&rsquo;t understand how they work which
leads to frustration trying to get it to do what they want. In this article, we&rsquo;ll build
our own mini-version manager from scratch and along the way you&rsquo;ll get an idea of how they
work under the hood.</p>10 features in rtx you may have missedhttps://jdx.dev/posts/2023-04-08-10-rtx-features/Sat, 08 Apr 2023 00:00:00 +0000https://jdx.dev/posts/2023-04-08-10-rtx-features/<p>Goal #1 with <a href="https://rtx.pub" class="external-link" target="\_blank" rel="noopener">rtx</a> was to be a drop-in replacement for <a href="https://asdf-vm.com" class="external-link" target="\_blank" rel="noopener">asdf</a>.
We quickly
achieved parity with asdf and now thousands of people have moved to rtx and are loving how much
faster and easier to use it is.
Since then, though, we haven&rsquo;t stopped and a lot more features have been added you might not
have seen.</p>
<h2 id="1-arbitrary-env-vars">1. Arbitrary env vars <a class="heading-anchor" href="#1-arbitrary-env-vars" aria-label="Link to 1. Arbitrary env vars">#</a></h2>
<p>You can now set arbitrary environment variables in your <code>.rtx.toml</code> files so now you can use rtx
as a replacement for dotenv and common uses of direnv:</p>Beginner's Guide to rtxhttps://jdx.dev/posts/2023-03-04-beginners-guide-to-rtx/Sat, 04 Mar 2023 00:00:00 +0000https://jdx.dev/posts/2023-03-04-beginners-guide-to-rtx/<p><a href="https://dev.to/jdxcode/beginners-guide-to-rtx-ac4" class="external-link" target="\_blank" rel="noopener">https://dev.to/jdxcode/beginners-guide-to-rtx-ac4</a></p>Introducing chimhttps://jdx.dev/posts/2022-09-04-introducing-chim/Mon, 05 Sep 2022 00:00:00 +0000https://jdx.dev/posts/2022-09-04-introducing-chim/<p><em>I had a 3-day weekend and decided to learn Rust while also putting together an idea I&rsquo;ve
had for a few years now: <a href="https://chim.sh" class="external-link" target="\_blank" rel="noopener">chim</a>.</em></p>
<h1 id="background">Background <a class="heading-anchor" href="#background" aria-label="Link to Background">#</a></h1>
<p>The problem I&rsquo;ve wanted to solve is bootstrapping projects for local dev and CI/CD.
Essentially, how tool versions are defined and installed—tools being things like programming
language runtimes, package managers, and linters. For example, a project might require node-v18.8.0, jq-v1.6, and shellcheck-v0.8.0. Other versions of these tools may not be compatible.</p>10 Tips for Ramping Up as a Senior Engineerhttps://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/Wed, 16 Sep 2020 00:00:00 +0000https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/<p>I&rsquo;ve learned the hard way that starting a job on a large engineering team as a senior engineer is more than simply writing good code. You have to drive initiatives at a social level and not simply because you know more about the codebase.</p>
<p>For a new hire this is especially a challenge. <strong>You need to learn the system that your colleagues already understand.</strong> You might be a higher level but you&rsquo;ll be a worse engineer for the first few months while you ramp up.</p>Async JavaScript Patterns for 2020https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/Sun, 19 Jan 2020 00:00:00 +0000https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/<p>I&rsquo;ve got a ton of different patterns I use when working with async code in JS. This article is a collection of them.</p>
<p>I&rsquo;ve split them into 3 parts: <a href="#promises" >Promises</a>, <a href="#asyncawait" >Async/Await</a> and <a href="#async-iterables" >Async Iterables</a>.</p>
<p>I see this as more of a ctrl-f reference for tasks like <a href="#promises-timing-out-a-promise" >&ldquo;how do I timeout a promise&rdquo;</a>. Though I&rsquo;ve also tried to keep it in rough order from beginner-advanced so if you want a comprehensive read of understanding async it should work well for that too.</p>Practical Guide to Closureshttps://jdx.dev/posts/2020-01-12-closures/Sun, 12 Jan 2020 00:00:00 +0000https://jdx.dev/posts/2020-01-12-closures/<blockquote><p>Closures are fairly common in JS but are also sometimes used in Go and Python and many other languages. This post is going to use JS but the concept is the same in all languages supporting closures.</p>
</blockquote><p>I found closures incredibly confusing for a long time—well after college and me working in the industry for years in fact. I found the concept confusing even when I was writing them all the time.</p>Pithy Guide to Kubernetes Part 2: Golanghttps://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/Sat, 07 Dec 2019 00:00:00 +0000https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-golang/<p>If you haven&rsquo;t done <a href="https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1" >Part 1</a> you&rsquo;ll need to start there.</p>
<p>In Part 1 we setup Minikube and added an Ingress, Service, and Deployment to the k8s cluster. Now
we&rsquo;ll finish that work by giving the Deployment an image to load.</p>
<p>The full example code is available on <a href="https://github.com/jdx/pithy-go" class="external-link" target="\_blank" rel="noopener">GitHub</a>.</p>
<h2 id="build-the-go-api">Build the Go API <a class="heading-anchor" href="#build-the-go-api" aria-label="Link to Build the Go API">#</a></h2>
<p>First initialize this directory as a Go module: \[optional, but recommended\]</p>
<div class="highlight"><pre tabindex="0" style="color:#f8f8f2;background-color:#282a36;-moz-tab-size:4;-o-tab-size:4;tab-size:4;-webkit-text-size-adjust:none;"><code class="language-sh" data-lang="sh"><span style="display:flex;"><span>$ go mod init
</span></span></code></pre></div><p>Now create a simple Go JSON API:</p>Pithy Guide to Kubernetes Part 2: Node.JShttps://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/Sat, 07 Dec 2019 00:00:00 +0000https://jdx.dev/posts/2019-12-07-pithy-guide-to-kubernetes-part-2-nodejs/<p>If you haven&rsquo;t done <a href="https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1" >Part 1</a> you&rsquo;ll need to start there.</p>
<p>In Part 1 we setup Minikube and added an Ingress, Service, and Deployment to the k8s cluster. Now
we&rsquo;ll finish that work by giving the Deployment an image to load.</p>
<p>The full example code is available on <a href="https://github.com/jdx/pithy-nodejs" class="external-link" target="\_blank" rel="noopener">GitHub</a>.</p>
<h2 id="build-the-node-api">Build the Node API <a class="heading-anchor" href="#build-the-node-api" aria-label="Link to Build the Node API">#</a></h2>
<p>First create a <code>package.json</code> file for our dependencies and add express to the app:</p>Pithy Guide to Kubernetes Part 1https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/Fri, 06 Dec 2019 00:00:00 +0000https://jdx.dev/posts/2019-12-06-pithy-guide-to-kubernetes-part-1/<p>This is a concise, opinionated guide to Kubernetes. I&rsquo;m assuming you already know how to build
software and are just looking to get started with Kubernetes. This is a 2-parter: the first is
language-agnostic and the second is for a particular language. I have Go and Node right now.</p>
<p>Assume we want to build a JSON web server managed by Kubernetes. At the end of this guide, we will
be able to do this:</p>\[video\] oclifconf: The Future of oclifhttps://jdx.dev/posts/2019-08-22-the-future-of-oclif/Thu, 22 Aug 2019 00:00:00 +0000https://jdx.dev/posts/2019-08-22-the-future-of-oclif/<p><a href="https://www.youtube.com/watch?v=1TKh2YBxRMY" class="external-link" target="\_blank" rel="noopener">https://www.youtube.com/watch?v=1TKh2YBxRMY</a></p>Golang Function Driven Testshttps://jdx.dev/posts/2019-05-09-go-function-driven-tests/Thu, 09 May 2019 00:00:00 +0000https://jdx.dev/posts/2019-05-09-go-function-driven-tests/<p><a href="https://dave.cheney.net/2019/05/07/prefer-table-driven-tests" class="external-link" target="\_blank" rel="noopener">Dave Cheney had a fantastic post on improving test structure in Go code with table-driven tests.</a> I want to expand on it just a tiny bit to show how table-driven tests can be made more concise with functions.</p>
<p>If you haven&rsquo;t read his article, read that before continuing.</p>
<p>The end result of Dave&rsquo;s post is the following example:</p>
<div class="highlight"><pre tabindex="0" style="color:#f8f8f2;background-color:#282a36;-moz-tab-size:4;-o-tab-size:4;tab-size:4;-webkit-text-size-adjust:none;"><code class="language-go" data-lang="go"><span style="display:flex;"><span><span style="color:#8be9fd;font-style:italic">func</span> <span style="color:#50fa7b">TestSplit</span>(t <span style="color:#ff79c6">\*</span>testing.T) {
</span></span><span style="display:flex;"><span> tests <span style="color:#ff79c6">:=</span> <span style="color:#8be9fd;font-style:italic">map</span>\[<span style="color:#8be9fd">string</span>\]<span style="color:#8be9fd;font-style:italic">struct</span> {
</span></span><span style="display:flex;"><span> input <span style="color:#8be9fd">string</span>
</span></span><span style="display:flex;"><span> sep <span style="color:#8be9fd">string</span>
</span></span><span style="display:flex;"><span> want \[\]<span style="color:#8be9fd">string</span>
</span></span><span style="display:flex;"><span> }{
</span></span><span style="display:flex;"><span> <span style="color:#f1fa8c">&#34;simple&#34;</span>: {input: <span style="color:#f1fa8c">&#34;a/b/c&#34;</span>, sep: <span style="color:#f1fa8c">&#34;/&#34;</span>, want: \[\]<span style="color:#8be9fd">string</span>{<span style="color:#f1fa8c">&#34;a&#34;</span>, <span style="color:#f1fa8c">&#34;b&#34;</span>, <span style="color:#f1fa8c">&#34;c&#34;</span>}},
</span></span><span style="display:flex;"><span> <span style="color:#f1fa8c">&#34;wrong sep&#34;</span>: {input: <span style="color:#f1fa8c">&#34;a/b/c&#34;</span>, sep: <span style="color:#f1fa8c">&#34;,&#34;</span>, want: \[\]<span style="color:#8be9fd">string</span>{<span style="color:#f1fa8c">&#34;a/b/c&#34;</span>}},
</span></span><span style="display:flex;"><span> <span style="color:#f1fa8c">&#34;no sep&#34;</span>: {input: <span style="color:#f1fa8c">&#34;abc&#34;</span>, sep: <span style="color:#f1fa8c">&#34;/&#34;</span>, want: \[\]<span style="color:#8be9fd">string</span>{<span style="color:#f1fa8c">&#34;abc&#34;</span>}},
</span></span><span style="display:flex;"><span> <span style="color:#f1fa8c">&#34;trailing sep&#34;</span>: {input: <span style="color:#f1fa8c">&#34;a/b/c/&#34;</span>, sep: <span style="color:#f1fa8c">&#34;/&#34;</span>, want: \[\]<span style="color:#8be9fd">string</span>{<span style="color:#f1fa8c">&#34;a&#34;</span>, <span style="color:#f1fa8c">&#34;b&#34;</span>, <span style="color:#f1fa8c">&#34;c&#34;</span>}},
</span></span><span style="display:flex;"><span> }
</span></span><span style="display:flex;"><span>
</span></span><span style="display:flex;"><span> <span style="color:#ff79c6">for</span> name, tc <span style="color:#ff79c6">:=</span> <span style="color:#ff79c6">range</span> tests {
</span></span><span style="display:flex;"><span> got <span style="color:#ff79c6">:=</span> <span style="color:#50fa7b">Split</span>(tc.input, tc.sep)
</span></span><span style="display:flex;"><span> <span style="color:#ff79c6">if</span> !reflect.<span style="color:#50fa7b">DeepEqual</span>(tc.want, got) {
</span></span><span style="display:flex;"><span> t.<span style="color:#50fa7b">Fatalf</span>(<span style="color:#f1fa8c">&#34;%s: expected: %v, got: %v&#34;</span>, name, tc.want, got)
</span></span><span style="display:flex;"><span> }
</span></span><span style="display:flex;"><span> }
</span></span><span style="display:flex;"><span>}
</span></span></code></pre></div><p>This is a nice way to reduce code duplication, but closing over a new function we can go one step further:</p>\[podcast\] codeish: oclif: An Open Source CLI Frameworkhttps://jdx.dev/posts/2019-05-07-oclif-an-open-source-cli-framework/Tue, 07 May 2019 00:00:00 +0000https://jdx.dev/posts/2019-05-07-oclif-an-open-source-cli-framework/<p><a href="https://www.heroku.com/podcasts/codeish/13-oclif-an-open-source-cli-framework" class="external-link" target="\_blank" rel="noopener">https://www.heroku.com/podcasts/codeish/13-oclif-an-open-source-cli-framework</a></p>\[video\] NodeConf: Building Great CLI Experiences in Node.jshttps://jdx.dev/posts/2018-10-17-nodeconf-building-great-cli-experiences-in-node/Thu, 18 Oct 2018 00:00:00 +0000https://jdx.dev/posts/2018-10-17-nodeconf-building-great-cli-experiences-in-node/<p><a href="https://www.youtube.com/watch?v=Izx3-KSuaM8" class="external-link" target="\_blank" rel="noopener">https://www.youtube.com/watch?v=Izx3-KSuaM8</a></p>12 Factor CLI Appshttps://jdx.dev/posts/2018-10-08-12-factor-cli-apps/Mon, 08 Oct 2018 00:00:00 +0000https://jdx.dev/posts/2018-10-08-12-factor-cli-apps/<p><a href="https://medium.com/@jdxcode/12-factor-cli-apps-dd3c227a0e46" class="external-link" target="\_blank" rel="noopener">https://medium.com/@jdxcode/12-factor-cli-apps-dd3c227a0e46</a></p>\[video\] DevRelCon: Designing a delightful command line interfacehttps://jdx.dev/posts/2018-07-16-devrelcon-designing-a-delightful-command-line-interface/Mon, 16 Jul 2018 00:00:00 +0000https://jdx.dev/posts/2018-07-16-devrelcon-designing-a-delightful-command-line-interface/<p><a href="https://www.youtube.com/watch?v=Izx3-KSuaM8" class="external-link" target="\_blank" rel="noopener">https://www.youtube.com/watch?v=Izx3-KSuaM8</a></p>For the love of god, don’t use .npmignorehttps://jdx.dev/posts/2018-05-25-for-the-love-of-god-dont-use-npmignore/Fri, 25 May 2018 00:00:00 +0000https://jdx.dev/posts/2018-05-25-for-the-love-of-god-dont-use-npmignore/<p><a href="https://medium.com/@jdxcode/for-the-love-of-god-dont-use-npmignore-f93c08909d8d" class="external-link" target="\_blank" rel="noopener">https://medium.com/@jdxcode/for-the-love-of-god-dont-use-npmignore-f93c08909d8d</a></p>Salesforce Blog: Open Sourcing oclif, the CLI Framework that Powers Our CLIshttps://jdx.dev/posts/2018-03-20-open-sourcing-oclif-the-cli-framework-that-powers-our-clis/Tue, 20 Mar 2018 00:00:00 +0000https://jdx.dev/posts/2018-03-20-open-sourcing-oclif-the-cli-framework-that-powers-our-clis/<p><a href="https://engineering.salesforce.com/open-sourcing-oclif-the-cli-framework-that-powers-our-clis-21fbda99d33a" class="external-link" target="\_blank" rel="noopener">https://engineering.salesforce.com/open-sourcing-oclif-the-cli-framework-that-powers-our-clis-21fbda99d33a</a></p>Heroku Blog: Evolution of the Heroku CLI: 2008-2017https://jdx.dev/posts/2017-08-15-evolution-of-the-heroku-cli/Tue, 15 Aug 2017 00:00:00 +0000https://jdx.dev/posts/2017-08-15-evolution-of-the-heroku-cli/<p><a href="https://blog.heroku.com/evolution-of-heroku-cli-2008-2017" class="external-link" target="\_blank" rel="noopener">https://blog.heroku.com/evolution-of-heroku-cli-2008-2017</a></p>How to Pair Programhttps://jdx.dev/posts/2015-02-03-how-to-pair-program/Tue, 03 Feb 2015 00:00:00 +0000https://jdx.dev/posts/2015-02-03-how-to-pair-program/<p><a href="https://medium.com/@jdxcode/how-to-pair-program-d6741077e513" class="external-link" target="\_blank" rel="noopener">https://medium.com/@jdxcode/how-to-pair-program-d6741077e513</a></p>\[book\] Write Modern Web Apps with the MEAN Stackhttps://jdx.dev/posts/2014-10-05-write-modern-webapps-with-the-mean-stack/Sun, 05 Oct 2014 00:00:00 +0000https://jdx.dev/posts/2014-10-05-write-modern-webapps-with-the-mean-stack/<p><a href="https://www.amazon.com/Write-Modern-Apps-MEAN-Stack/dp/0133930157" class="external-link" target="\_blank" rel="noopener">https://www.amazon.com/Write-Modern-Apps-MEAN-Stack/dp/0133930157</a></p>Best Practices for Building Angular.JS Appshttps://jdx.dev/posts/2014-07-09-best-practices-for-building-angular-apps/Wed, 09 Jul 2014 00:00:00 +0000https://jdx.dev/posts/2014-07-09-best-practices-for-building-angular-apps/<p><a href="https://medium.com/@jdxcode/best-practices-for-building-angular-js-apps-266c1a4a6917" class="external-link" target="\_blank" rel="noopener">https://medium.com/@jdxcode/best-practices-for-building-angular-js-apps-266c1a4a6917</a></p>Older Postshttps://jdx.dev/posts/2014-01-01-older\_posts/Wed, 01 Jan 2014 00:00:00 +0000https://jdx.dev/posts/2014-01-01-older\_posts/<p>You can view my older posts on medium: <a href="https://medium.com/@jdxcode" class="external-link" target="\_blank" rel="noopener">https://medium.com/@jdxcode</a></p>Membershttps://jdx.dev/members.htmlMon, 01 Jan 0001 00:00:00 +0000https://jdx.dev/members.htmlSponsorshttps://jdx.dev/sponsors.htmlMon, 01 Jan 0001 00:00:00 +0000https://jdx.dev/sponsors.html