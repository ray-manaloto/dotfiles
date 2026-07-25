# Graphify + Obsidian is INSANE: Build an AI Second Brain That Never Forgets

Source: https://www.youtube.com/watch?v=22iy2mDFiF8
Type: video transcript (YouTube auto-captions)

This is an AI second brain that never forgets.

Point it at a folder and your whole project turns into a graph your assistant can query because right now your coding assistant has amnesia.

Every new chat it has read nothing.

Ask it how your login flow works and it opens every file from scratch to figure it out.

Do that across 200 files on every single question and you pay a token tax each time.

And stuffing your entire repo into a giant context window just makes the answers worse.

On April 3rd, Andre Carpathy posted a fix and the dev world copied it in a single weekend.

Stop making the model rebuild your knowledge every query.

Give it a wiki it keeps up to date itself. 2 days later, a developer shipped exactly that as a tool called Graphify.

From nothing, it blew past 90,000 GitHub stars in about 3 months.

Pair it with Obsidian, and that graph becomes plain Markdown you own.

So, here's the full picture.

How graphify builds the graph, why Obsidian is its home, and the four ways it falls apart if you get lazy.

And this was not some quiet launch.

It turned into a genuine wave.

That claude code plus Obsidian idea pulled over 50,000 likes on X in a single week.

One post declaring notetaking dead hit 54,000 on its own.

Carpathy's little gist alone picked up 14,000 stars and,900 forks.

First, the actual problem Graphify is solving.

The usual fix for a big code base is what's called rag.

Chop your files into chunks, turn them into vectors, and search for the closest matches when you ask a question.

That works great for pros.

For code, it's shaky because the link between a function and the things that call it isn't about similar words.

It lives in the call graph.

You end up paying to load the whole library just to find one paragraph.

Graphify flips that around.

Instead of searching text on every question, it does the expensive reading once up front and squeezes your project into an explicit graph of entities and the relationships between them.

After that, answering a question means walking the graph instead of rereading the files.

It's exactly how a senior engineer works.

Build the mental map once, then just follow it.

And it isn't only code.

Graphify pulls in your SQL schemas, your shell scripts, your R notebooks, your architecture PDFs, even recorded videos, and drops them into one graph.

Application code, database schema, and infrastructure finally living on the same map instead of in five different heads.

Actually using it is almost boring in the best way.

Inside cloud code or codeex or cursor, you type /graphify and point it at a directory.

It grinds through the folder and drops a graphify out folder right next to your code with the entire graph saved to disk.

It supports every big assistant, not just one.

Here's the part one genuinely respect.

Graphify does not treat every file the same way.

It runs three separate passes over your stuff and each one has a completely different story about where your data ends up.

Pass one is your source code.

Graphy runs it through tree sitter, the same kind of parser a compiler uses across 40 languages.

It's deterministic.

There's no AI model involved and there's no network call.

Your code stays on your machine and every link it finds gets tagged as a hard fact.

Pass two is for recordings.

Point it at a folder with audio or video, say a design meeting you screen recorded, and it transcribes them locally with faster whisper.

An hour of talking becomes text right on your laptop and folds into the graph.

Nothing gets uploaded.

Pass 3 is the honest one.

Documents and images, a PDF spec, or a photo of a whiteboard can't be read by a grammar.

So, those get sent to your AI provider to be understood.

That's the only pass that leaves your machine, and it goes to your own API key, not some middleman.

Want it fully private?

Run code only mode and skip this pass.

And it refuses to sound sure about things it isn't.

Every connection in the graph carries a label.

Extracted means it's right there in your code, so trust it.

Inferred means the model reasoned it from context.

So probably ambiguous means the model itself raised a hand.

So check before you build on it.

Once the graph exists, it organizes itself.

Graphify runs community detection and your modules just fall out of the shape of the code.

O in one cluster, billing in another, infrastructure off on its own with the bridge files between them lit up.

You didn't draw that map.

The relationships did.

Now the payoff at query time.

You ask, "How does a user log in?" Instead of loading 50 files, Graphify walks the graph and hands back a short path.

Three hops, zero files opened.

Your assistant reads a few node summaries instead of half the repo.

And querying isn't just one trick.

Graphify explain hands you a plain English tour of any entity.

Graphy path finds the shortest chain between two things, say auster and the database pool it secretly leans on. and deep mode goes hunting for the fuzzier inferred links a quick pass would skip right over.

Graphy puts a number on all this about 71 times fewer tokens per query on a mixed codebase.

Now that's their own benchmark on their own data and nobody outside has reproduced it yet.

So take the exact figure with a grain of salt, but the direction is obviously right.

Walking a map is cheaper than rereading the whole library every time.

And that one graph isn't trapped inside the tool.

Graphy exports it every way you'd want. a clickable HTML graph rendered with viz.s s plain JSON for scripts, a markdown report of your busiest files, a Neo4j database, even an MCP server, so any agent can call your codebase graph like a built-in tool.

It also stays current without you babysitting it.

Every file gets a chat 256 hash, so the second run only rereads what actually changed.

Add a git hook and the graph rebuilds itself on every commit.

Your assistant sees a map that matches the exact branch you're standing on.

So, where does Obsidian fit?

Obsidian is a notes app built on plain markdown files that live on your disc, not on someone's server.

Around 1 and a.5 million people use it, and its plugins just crossed 100 million downloads.

It's the natural home for a brain you actually want to own.

Point Graphifies Obsidian export at a vault, and your graph turns into real notes.

Every entity becomes a page.

Every relationship becomes a Wiklink.

And Obsidian's graph view shows the whole thing as a web.

You can wander through your codebase as a mind map.

You can open on a Sunday.

Then you close the loop with a plugin like Claudian, which drops Claude code straight into the Obsidian sidebar.

Your vault becomes the agents working directory.

It can read your notes, write new ones, and run commands without leaving the app your knowledge already lives in.

And Graphify isn't the only door in.

You don't have to hand over full write access on day one.

Smart connections just surfaces related notes using embeddings.

Cudge is the self-hosted run it all locally option.

Copilot for Obsidian gives you vault are chat and is already past 100,000 users.

Start light then give it more rope.

Underneath all of this sits Carpathy's actual design and it's refreshingly simple.

Three layers.

A raw folder of sources the AI leaves untouched.

A wiki layer the AI does own where it writes pages and keeps the cross links honest.

And a schema file that tells the model how your wiki is laid out.

Three operations keep that wiki alive.

Ingest pulls in new sources and updates every page they touch.

Query searches the wiki and answers you with citations.

And lint runs a health check for contradictions, dead pages, and stale claims.

Remember that word lint.

It comes back to bite people.

And what gets me is how old this idea actually is.

Carpathy traces it back to 1945 to Vanavar Bush's memes.

The dream of link trails between your documents.

The links mattered as much as the pages themselves.

We just lacked a tool patient enough to maintain them.

Now the model does that upkeep for free.

Okay, I've talked this up for 5 minutes, so let me be the annoying person in the comments for a second.

The viral demos leave out the part where this whole thing rots if you ignore it.

There are four cracks worth knowing about.

Crack one is size.

A vault with 50 tidy notes feels like actual magic.

A vault with 2,000 notes turns into a search problem all over again because the model spends its context just navigating your structure instead of answering your question.

The graph softens that.

It doesn't erase it.

Crack 2 is confident fiction.

When the assistant writes up your notes, it cheerfully fills the gaps with things you never said in your own voice.

The fix is a blunt line in your instructions.

Do not add anything I didn't write.

Without that rule, your second brain starts inventing memories.

Crack three is feedback loops.

The AI writes a page, then weeks later cites its own page as a source, then builds on top of that.

Let it run unattended and you get AI quoting AI where small mistakes slowly harden into facts.

Your brain fills up with its own echo.

Crack 4 is the big one, and it's why that word lint mattered.

Carpathy built a cleanup pass into the design on purpose, and almost every tutorial skips it. 5 minutes a week, read what the agent wrote, prune the stale pages, kill the contradictions.

Skip that and the whole thing decays into noise.

Do it and it compounds into something real.

So, my honest take, a second brain that never forgets is genuinely here and it's the best version we've had.

But that memory cuts both ways.

It also keeps every bad note and lazy guess unless you clean up after it.

Own your markdown, keep it on your disc, and treat that weekly lint pass as the rent.

And if you do one thing this week, start almost embarrassingly small.

One folder, one graph, one vault.

Let it earn your trust on a project you already understand before you feed it your entire life.

The people who win with this aren't the ones with the sickest demo.

They're the ones whose vault still tells the truth 3 months from now.

That's the whole build.

A brain that finally keeps up with you.

See you in the next one.
