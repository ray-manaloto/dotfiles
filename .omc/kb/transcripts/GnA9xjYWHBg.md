# Graphify + Claude Code + Obsidian = GOD MODE

Source: https://www.youtube.com/watch?v=GnA9xjYWHBg
Type: video transcript (YouTube auto-captions)

This is probably the best way to give Claude code a high quality knowledge base or memory system in minutes.

Essentially, we're going to take the current workspace that you already have.

We're going to use Graphify to turn it into a knowledge base with a bunch of nodes with relationships.

We're going to import that into Obsidian, and then we're going to let Claude code work out of that Obsidian database so that it has a deeper and more contextual understanding of your workspace.

And so, here is an example of one of the workspaces that I use on a daily basis.

Uh it's essentially one for my meditation practice.

I have a bunch of core ideas related to meditation, Dharma talks, etc.

So, I basically pointed uh Graphify at that.

You can see how many different nodes, relationships, etc. there are between them.

And then here I imported this into Obsidian, and you can see that Obsidian now has access to all these different concepts.

Um and then we're going to relate all of these together and point Claude code at this Obsidian workspace.

So, the first thing that I want to dive into is how do essentially create this Graphify knowledge base, um and then how to turn it into an Obsidian uh vault.

And so, the first thing we're going to do is we're going to basically just open up uh Claude code inside of our workspace.

So, whether you're using terminal, something like anti-gravity, even if you're using it in Claude uh directly, uh you can see here Claude code.

Uh I'm having this in a workspace, so maybe I can do this from scratch to show you what this would look like.

Essentially, what we're going to do is use Graphify um to to build this out.

So, what I'm going to do is open Claude code.

I'm going to open it in a workspace, and I'm going to say, "Once you have the Graphify plugin set up, I'm not going to teach you how to set this up." I have a couple other videos on that.

But, what you can do is go to Graphify, um and then you can essentially uh go to GitHub Graphify.

Um and there is the GitHub repo.

You'll find that in the description below.

This will essentially show you how to use it, um how to set it up.

Essentially, it's a really quick install.

It's a plug-in inside of Quad Code uh that will work in any database.

And so, now what we're going to do here is we're essentially going to say, "I want you to use Graphify and create uh a Graphify knowledge base based on this workspace." So, that's pretty much the command once you set up the plug-in.

So, {forward slash} plug-in is how you will set this up.

Um then it will be installed.

You'll use Graphify to create the knowledge base.

And then it's essentially going to do this.

It's going to run this skill.

It's going to create the knowledge base.

And then it's not going to change any of the files in your uh directory.

All it's going to do is create like a new basically web or knowledge base on top of that, uh which is what we're seeing here.

So, I'm going to let this run for a second.

It's going to create that knowledge base inside of I'm basically building an agentic operating system and it's we're essentially going to graphify so we can understand the code base.

And so, now with that being said, um another thing here is uh you know, it's essentially going to create this knowledge base.

So, you'll see here I basically had it do that.

It went through every single file in this directory.

And then you you can see it's creating all these nodes, all these connection.

An edge is basically a connection.

Um and now if I go almost to the bottom here, you can see I said, "Now use the Graphify Obsidian command to turn this into a vault." That's pretty much how simple it is.

So, once um you create the Graphify uh basically system, it lives inside of a folder.

It's pretty much separate from everything else.

You know, it's it's its own way of just understanding a code base.

And so, essentially once you run that, you will see something called Graphify out.

That is the folder that Graphify creates whenever it's running this skill.

Uh and what you can do if you want to see this actual graph, cuz sometimes it's not obvious.

If you want to see this graph of your system, this is the graph.html.

You'll just click reveal in finder.

Um you'll see something like this.

And then you'll just double click on this file, and that's the HTML file that shows it.

But, this is still not connected to our Obsidian.

We could point Obsidian at this vault and open this inside of Obsidian, but it's not going to work very well because it's it's using different methods than Obsidian uses.

It's not all markdown files.

And so, what you'll do is, like I said, once it creates that Graph-of-Ideas system, then you'll say, "Now use the Graph-of-Ideas Obsidian command to turn this into a vault." And then essentially what it will do is it take you We'll see 2,186 notes, one per node, in our vault.

So, now if I go into the vault into the vault, the only problem is that a lot of these nodes don't have the full context.

So, let's say I look at The Way of Non-Clinging.

This relates to a lot of different connections, but in each of these connections, we don't see too much about the actual page.

This is a, you know, a Dharma talk advanced Dharma talk from my teacher Robert Beah, and he's talking about this idea of soul-making and metaphysics, ontology, emptiness, dependent origination, all these like really advanced things.

But, we see there's not actually that much context in these pages.

So, how would I actually turn this and make sure that the context from the workspace gets ported in directly?

Because we can see when Graph-of-Ideas creates it, it just basically creates a bunch of nodes.

So, it's basically relating all the concepts together, but it's not necessarily inputting all of the context that we need inside of each of these nodes.

Like, views profoundly shape perception and experience.

You know, it's just relating it to nodes, which is still valuable because now the AI kind of knows what concepts are related.

But, if we want to actually make this powerful for Quad Code, it needs to have the context in it.

And so, how do we actually do that?

The next thing that we're going to do is, once it creates this Obsidian vault, we're just going to say something like, "Now I want you to reintegrate all of the context from this workspace into the Obsidian folder." And so, I'm linking the path above of the Obsidian folder, and I basically want you to take any of the context from the Dharma talks, from any of my journal entries, the articles I've written, the books, any of the the markdown context that exists in this workspace.

I want you to reintegrate it into the Obsidian vault so that any of the markdown files in that folder actually have the context, not just the relationships. &gt;&gt; [snorts] &gt;&gt; And you can see basically what I did is I right-clicked on this folder, clicked copy path, and then I'm basically just using natural language to tell it what to do.

And I'm basically saying, we might even say like something like {forward slash} loop over or goal don't stop.

Don't stop until every node has its relevant context and every markdown file [clears throat] in this workspace has [snorts] its context duplicated into the relevant nodes, plural.

And so, if this doesn't get it on a one-shot, then we'll run a goal on this, or we could even say loop over every single file, or we could just say goal don't stop.

It's going to have the same output where it's going to go over all of the different files.

And so, I'm going to let this run for a second.

We can see that there's 2,186 nodes in this workspace.

And so, it's going to take a while to edit this, but essentially what we're doing is we're letting it go and populate all of these files with the relevant documentation.

So, this is finished up, and now we can essentially see that after it finished, if we go back into Obsidian, the there's more nodes, there's more connections.

All of these nodes have source content in them.

So, if I click on one of these, opening the Dharma of desire, we can see the source content is linked.

We have a full context shaped in from all of the different notes, all of the different files.

Um and you can see that it is quite a lot of context here.

Um and the full transcripts and the full markdown files, etc., are in here.

Now, the last thing that we're going to do and how we would set this up is I would go click create file new window um [snorts] inside of anti-gravity.

Um I guess we were working inside of Quad Code as well.

Um and so, this is you know, it'd be the same thing inside of Quad Code.

I kind of skipped over that, but it'd be the same exact thing.

You would just open a new folder down here in a new tab.

But, what we're going to do is open a new folder.

I'm going to go ahead and actually find that.

So, if I go over here into Ethan Nelson Buddhist practice, graphify Obsidian.

That is essentially the new knowledge base.

And if I open this, um now we are essentially having Quad Code route into this new knowledge graft version.

And you can see it's just a bunch of markdown files here.

Um but essentially how this works is now if I started a Quad Code chat directly in here, what would happen is I could say, uh "How does uh the Dharma of desire relate to the concept of arrows and dimensionality?" And the ontological uh pitfalls of uh Buddhism as Rob Brebea teaches it.

So, this is a like very like hyper-specific question um that usually it would take a crap ton of time to go and grep or or pull all these files, read all of them, etc.

And now what we're essentially seeing is that what's going to happen is it's going to go it's going to find the specific nodes.

It's going to use bash commands and grep commands still, but it's going to because the knowledge base is built, it's going to use specific skill specific nodes and it's going to know exactly where to look and it's going to take you know, maybe 30 seconds to find the exact piece of information because the knowledge base was built behind the scenes.

So we can see it ran only three bash commands to go and find look through these different nodes and markdown files and then it found the exact thing that it's looking for.

There are four teachings.

Here's the core threads.

The ontological pitfall is this.

It's pulling specific quotes.

It prized desire loose from craving, etc.

Eros is the desire that opens dimensionality.

Dimensionality is what Eros makes and why any of it matters.

And so this is like a very very solid this is almost exactly what this teacher teaches.

A flexible ontology emptiness that frees rather than flat ends.

And so this is like a very specific answer to a extremely complex database of concepts nodes.

Now I use this for a very specific example, but you could use this for anything whether it's you're building marketing projects, it's a code base, whatever.

It's going to be able to search through and find exactly what it needs with very very few tokens.

I would be Yeah, the token usage is probably going to be extremely low on this because we only ran like three bash commands.

So it's probably going to be, you know, like a few hundred tokens, maybe a thousand tokens max.

And so I hope this was valuable.

Thank you so much for watching.

And check out the links in the description if you want to learn more about Claude code, how to set up these memory systems, agentic operating systems, etc.

And I will see you in the next video.

Cheers.
