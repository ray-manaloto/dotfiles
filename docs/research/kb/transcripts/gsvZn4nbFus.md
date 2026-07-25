# Fable 5 + GPT 5.6 Sol = CHEAT CODE

Source: https://www.youtube.com/watch?v=gsvZn4nbFus
Type: video transcript (YouTube auto-captions)

GPT 5.6 aka Soul is coming out tomorrow and the big question on everyone's mind is does this new model beat Claude Fable?

Well, I think that's the wrong question to ask because instead of trying to figure out which one of these models is better, we should be asking how can we use these two powerful models together?

And in today's video, I'm going to be giving you a skill that does exactly that.

This skill includes a supercharged plan mode based on Matt PCO's Grill Me.

We then have an adversarial planning session where Claude and Codex go headto-head till they come to a conclusion.

Then once we're ready, we take that Fabled driven plan and hand it off to Codeex, which starting tomorrow will include Soul 5.6.

After Codeex goes to work, then we have Fable review the entire process.

All in all, we're not just getting the best of both of these models, we're also saving tokens in the aggregate versus having Fable do everything.

So, I'm going to show you how this works.

We're going to do a quick demo and then I'll be giving you the skill.

So why should we even care about creating some sort of skill where Fable does most of the planning and then we pass it off to Soul 5.6?

Well, first reason is Soul 5.6 is wildly powerful, at least according to the benchmarks.

Now, grain of salt, this is coming from OpenAI, but when we look at Soul 5.6 Ultra and just standard 5.6 six soul.

We see numbers on Terminal Bench 2.1 that put it ahead of Claude Mythos, let alone Fable 5.

The second reason is token efficiency.

There is a real reason why you see so much content around, hey, how can we reduce Fable's usage and the types of things you see are like advisor mode.

You know, essentially having Fable plan and have Opus execute.

Well, why have Opus execute if with at the same price I could have 5.6 do it or 5.5 do it?

Point is, we're doing that same construct but with a better model and arguably a cheaper model than Opus.

When we look at 5.6, it is more token efficient than 5.5 which was more token efficient than Opus 4.6.

And we can see that in the data.

What we're looking at right here is GPT 5.5 on extra high.

Its pass rate on this benchmark was 23% at $1.24.

When I look at 5.6, six, it's 25% score, so higher score at 56.

So way cheaper and therefore way more efficient.

And when we look at direct comparisons of 5.5 versus Opus 4.8, there's really no contest.

Higher pass rates, lower cost.

So we're essentially taking that same idea and just ramping it up with this 5.6 improvement.

So how does this skill actually work?

Well, I actually have a couple skills for you.

In a vacuum, we have the codeex build skill.

This is the idea that you created a plan with Fable and Codex is just going to go ahead and build that particular feature or particular product.

I also have included an updated grillme codeex.

Now, I've done a video on this skill before and what we've done is we've added on this idea of GPT 5.6 actually going out there and building things for us.

And so, when we look at the more comprehensive GMI codeex, which is the big skill, it occurs in four stages.

The idea is you have some sort of project, some sort of feature you want to start and you kick it off with grill me codeex and the first thing that happens is an interview.

This interview is literally the grill me skill from Matt PCO.

So it is a plan mode on steroids.

It goes way way deeper than Claude Code normally would.

And we do this with Fable.

All right.

So Fable's driving the ship here.

Secondly, we have adversarial planning.

So Fable's come up with a plan.

We then take that Fable plan and we push it over to Codeex.

Now, in today's video, that's going to be 5.5, but tomorrow that will be 5.6.

And Fable and Codex go back and forth for a maximum of five iterations where Fable says, "Hey, here's the plan." Codex says, "Okay, looks good.

Accept X, Y, and Z." Then Fable says, "Uh, I agree, I disagree." And they go back and forth till they reach a consensus.

Now once they reach that consensus and this is where the upgrades happen is we now push the actual build to codeex to 5.5 today and 5.6 tomorrow.

I think this is way better than passing things off to Opus or to Sonnet or using advisor mode inside of cloud code because these GPT models are just better than those smaller anthropic models and they are cheaper.

So, it really is a scenario where unless you just are super anti-GPT and anti-codex, it's hard to argue otherwise, especially if we get to a place where Fable is like kind of off the market.

And lastly, once Codeex finishes the build, Fable is going to come in and it's going to review what it did and it's going to go through a maximum of two sort of iterations where, let's say, Fable thinks Codex did something wrong.

It's going to say, "Hey, Codex, you did that wrong.

Fix it." It's going to do that twice.

If by the third time it's not complete, well then Fable will clean it up itself.

So this is the process by which I think we get the best of OpenAI and Anthropic.

Now before we hop into the demo, a quick word from today's sponsor, me.

So I just released my Cloud Code master class inside of Chase AI plus and it is the number one way to go from zero to AI dev, especially if you don't come from a technical background.

I update this every single week.

We focus on real use cases and it also includes a codeex masterass as well.

So, if you want to get a little bit more serious about AI and you have no idea where to begin, this is the place for you.

There will be a link in the pin comment.

Now, installing and using the skill is pretty straightforward.

I will put a link to the GitHub in the description.

Now, to use this, we're just going to do for/grill codeex.

And we just give it our prompt what it is we're trying to build.

So, we're trying to build trip atlas, which is a stylized cinematic trip planner web app.

And I go into a little bit more details about what I want it to be, right?

I want it to look kind of cool.

I can put in the different places I'm going, all that.

And once I do this, what's going to happen is it's going to kick off the grill me section of the plan, which if you're familiar with Matt PCO's work, it essentially is just a plan mode on steroids.

It's going to ask me like 8 n 10 different questions.

I go a lot deeper than your standard plan mode stuff.

So, it's asking me what is this for?

We're going to say this is for a real personal tool, not just a video demo.

And for each of these, it also gives its recommendations.

So, if you're confused about what I should choose and why, that's all spelled out for you.

Now it's asking about geocoding and it's going to continue to go down these series of questions until it's happy with what we're creating.

Now I'm going to skip through the rest of the questions because you can imagine what the next seven or eight questions will look like and we'll move into the adversarial planning stage.

So we can see here it's written the plan and it also creates a markdown file where it logs all the back and forth between codeex and cloud code.

And so right now we are on round one where it's passing it off to GBT.

And so you can see them kind of going back and forth here on the log.

But in this case, it only took them two rounds before it was approved.

And so we can see what the two acts improved.

You know, lock the identity, a real person tool, kind of what's going to be the actual sort of stack.

And then it had 12 findings in the second round related to like hardening the data core.

Now once it's completed this back and forth, you have a few options. either Codex is going to build it.

Kind of what we've talked about from the beginning.

We have the option just having Claude build it.

So for whatever reason like I don't want to bring GPT in, you can keep it with Fable or you can stop here.

But we're going to go ahead and let Codeex build this.

And again, we can kind of go back and forth.

If you think, well, GPT 5.6 is going to be better than Fable or 5.5 versus Opus 4.8.

At the end of the day, the real value that can't really be argued with is going to be the token efficiency, especially if 5.6 6 is even close to what the benchmarks are claiming.

So Codeex has finished up its build and you can see now what's happening is the review stage.

So now Fable is going through everything Codex has built and then it's going to go back to Codex and say this is wrong, this was right.

Remember it'll do two iterations of that before it's like hey I want to drive.

It'll take the wheel and it will start writing the code itself.

Now Fable is done with its review.

It said there were a couple deviations which it felt were all reasonable. goes over the files and all this and now it's asking, hey, do you want to commit or you want to take a look at it?

So, let's take a look at what it actually built.

And so, here's what we got.

So, over here we have sort of a map of the world and it looks like it created some custom graphics using the GPT image generator.

So, you're able to like name the trip, you can add stops.

Over here on the left, you can put where you're going and then sort of like what you're going to do at those different locations.

It also has this cinematic replay.

And I'm just going to mute this.

So, let's see what happens here.

So, it looks like I'll move over here.

You can see sort of this weird plane hopping from spot to spot, which it looks like it created as an SVG.

There's a little passport stamps and boom, there we go.

So, you know, there's a lot we could do here to kind of make it look, I think, better, but in general, it built what we said we wanted to, right?

Like everything actually works here.

You know, if I delete things on here, delete some.

I can move them up, down.

I can change stuff.

Let's say we added Tokyo.

All of a sudden, it actually shows how far away that stop is.

That's interesting.

If I add that to the route.

There we go.

So, you know, actually built this out.

I think it'd be a good not bad, I think, for the first pass.

And what this really was about was just showing this workflow in action.

And you can also see down here in terms of our usage, we only burned up about 130,000 tokens on the fable side to get this whole thing done.

So that's the skill in action.

Hopefully you get a ton of use out of this one's 5.6 drops.

As always, let me know what you thought about this video in the comments.

Make sure to check out Chase AI Plus and I'll see you
