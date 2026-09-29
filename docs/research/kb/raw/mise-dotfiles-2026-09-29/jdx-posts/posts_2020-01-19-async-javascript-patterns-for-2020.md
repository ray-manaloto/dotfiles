[Skip to content](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#main)

On this page

I’ve got a ton of different patterns I use when working with async code in JS. This article is a collection of them.

I’ve split them into 3 parts: [Promises](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises), [Async/Await](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait) and [Async Iterables](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables).

I see this as more of a ctrl-f reference for tasks like [“how do I timeout a promise”](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-timing-out-a-promise). Though I’ve also tried to keep it in rough order from beginner-advanced so if you want a comprehensive read of understanding async it should work well for that too.

These should work just as well whether you’re writing frontend or backend code.

## Table of Contents [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#table-of-contents)

- [Why Async?](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#why-async)
- [Promises](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises)
  - [Promises: Call an API](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-call-an-api)
  - [Promises: Running in Series](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-running-in-series)
  - [Promises: Waiting on parallel tasks](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-waiting-on-parallel-tasks)
  - [Promises: Turn an object into a promise](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-turn-an-object-into-a-promise)
  - [Promises: Manually creating promises to work legacy callbacks](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-manually-creating-promises-to-work-legacy-callbacks)
  - [Promises: `util.promisify`](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-utilpromisify)
  - [Promises: Order of operations](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-order-of-operations)
  - [Promises: Manually creating promises to encapsulate logic](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-manually-creating-promises-to-encapsulate-logic)
  - [Promises: A noop promise that just waits](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-a-noop-promise-that-just-waits)
  - [Promises: Timing out a promise](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-timing-out-a-promise)
  - [Promises: Memoizing with promises](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-memoizing-with-promises)
  - [Promises: `.finally()`](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-finally)
- [async/await](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait)
  - [async/await: Creating `async` functions](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-creating-async-functions)
  - [async/await: Errors](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-errors)
  - [async/await: Catching a single promise](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-catching-a-single-promise)
  - [async/await: `finally`](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-finally)
  - [async/await: Operations in series](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-operations-in-series)
  - [async/await: Operations in parallel](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-operations-in-parallel)
  - [async/await: Semi-parallel tasks](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-semi-parallel-tasks)
  - [async/await: Sleep](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#asyncawait-sleep)
- [Async Iterables](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables)
  - [Async Iterables: Basic Example](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-basic-example)
  - [Async Iterables: Log Server Example](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-log-server-example)
  - [Async Iterables: Transforms](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-transforms)
  - [Async Iterables: Testing Transform](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-testing-transform)
  - [Async Iterables: Buffering](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-buffering)
  - [Async Iterables: `tap(fn)`](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-tapfn)
  - [Async Iterables: `clone()`](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-clone)
  - [Async Iterables: Reading Node Streams](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-reading-node-streams)
  - [Async Iterables: Creating Node Readable Streams](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-creating-node-readable-streams)
  - [Async Iterables: Writing to Node Streams](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-writing-to-node-streams)
  - [Async Iterables: Error Handling](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-error-handling)
  - [Async Iterables: Communicating with iterable](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#async-iterables-communicating-with-iterable)
- [Footnotes](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#footnotes)

## Why Async? [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#why-async)

If you’re writing JS—frontend or backend—you’ll virtually always[1](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fn:1) have to write async. Partially because it’s the way we write efficient code but more importantly you’re not likely to find any libraries that are written synchronous to be able to work with.

On the frontend, the code is async because we never want to block the main thread. Doing so causes a webpage to freeze. On the backend, we want to keep the main thread[2](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fn:2) free because it allows us to accept more requests inside that same process.

Async is more complex to write than synchonous code because we allow multiple code paths to be running at the same time. E.g.: while we make a request to an API we can process other requests and do other tasks. That said, one major benefit of async is we have a lot of control over orchestrating tasks in parallel.

Promises are the basic method we use to specify a function to run when some async task is complete.

## Promises [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises)

Promises are what all the other async tools we use[3](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fn:3) are built on. A Promise is an Object, but it does not represent the return value of some task, it represents the running (or complete) task itself.

They represent a single task that will either complete or error out at some point (and never both). They have 2 primary methods, `.then()` and `.catch()` for registering a function to be called when it completes or errors.

You’ll rarely create Promises yourself—though as I [cover later](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#promises-manually-creating-promises-to-encapsulate-logic) you shouldn’t avoid doing so. Much more commonly the library you use will return a promise for you to interact with.

### Promises: Call an API [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-call-an-api)

Need to make a web request?

```javascript
// p is a promise
const p = fetch('https://jsonplaceholder.typicode.com/todos/1')

// we're registering a new function that will be called
// when the request is complete
p.then(response => {
  console.log('request OK')
})

// this is the same as above but more common syntax
// first I showed saving it into a variable so it's more clear what's happening
fetch('https://jsonplaceholder.typicode.com/todos/1')
.then(() => console.log('request ok'))
```

> If you’re writing node, you can use [node-fetch](https://www.npmjs.com/package/node-fetch) for this. In the browser you’ll already have this function.

### Promises: Running in Series [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-running-in-series)

A common mistake when learning Promises and trying to make calls in series is to do this:

```javascript
// get the list of todos
fetch('https://jsonplaceholder.typicode.com/todos')
.then(response => {
  console.log('request 1 OK')
  // DO NOT DO THIS
  fetch(`https://jsonplaceholder.typicode.com/todos/1`)
  .then(() => console.log('request 2 OK'))
})
.catch(err => {
  /* error handling */
})
```

A major bug here is that only the `/todos` call is handled if it errors. Rather than add an error handler at each step, with promises we can return new promises in the then handler and cascade any errors to a final `.catch()`:

```javascript
// get the list of todos
fetch('https://jsonplaceholder.typicode.com/todos')
.then(response => {
  console.log('request 1 OK')
  // get a single todo
  return fetch(`https://jsonplaceholder.typicode.com/todos/1`)
})
.then(() => console.log('request 2 OK'))
.catch(() => {
  /* errors from either promise will be handled here */
})
```

This builds a promise “chain” where the main benefit is that we don’t keep indenting for every new promise. It makes no difference at runtime[4](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fn:4), it just helps you as the developer read/write the code. _Note that promises inside promises will always be flattened so you never need to worry about “unwrapping” them more than once._

`fetch()`’s response has a method `.json()` which returns a promise of the response as JSON. We can build a promise chain here to make the call, parse the json, make another call, then parse that json.

```javascript
// get the list of todos
fetch('https://jsonplaceholder.typicode.com/todos')
.then(response => {
  return response.json()
})
.then(todos => {
  console.log(`got ${todos.length} todos`)
  // get a single todo
  return fetch(`https://jsonplaceholder.typicode.com/todos/${todos[0].id}`)
})
// because arrow functions return the value if it's on a single line
// we usually use this shorthand
.then(response => response.json())
.then(todo => {
  console.log(`got todo: ${todo.title}`)
  // we do not necessarily have to return a promise. If we just return a non-promise value
  // it will be passed to the next .then()
  return 101
})
.then(n => console.log(`101 === ${n}`))
```

With callbacks this would be nasty.

### Promises: Waiting on parallel tasks [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-waiting-on-parallel-tasks)

One of the great things about promises is how easy it is to run things in parallel compared to blocking code. All you need to do is start a few promises and wait for them all to complete with `Promise.all()`.

```javascript
const myPromises = [\
  fetch('https://jsonplaceholder.typicode.com/todos'),\
  fetch('https://jsonplaceholder.typicode.com/users'),\
]
Promise.all(myPromises)
.then(responses => {
  // all responses complete
  // do something with responses[0]
  // do something with responses[1]
})

// use array destructors so you don't have to manually index into the response arrays
Promise.all(myPromises)
.then(([todoResponse, userResponse]) => {
  // do something with todoResponse
  // do something with userResponse
})
```

The real great thing about promises is they give you a ton of control over when tasks start/stop.

### Promises: Turn an object into a promise [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-turn-an-object-into-a-promise)

From time to time, you need to wrap an object a promise but don’t need to do any async work. Use `Promise.resolve()` for this.

```javascript
const p = Promise.resolve('abc')
p.then(s => console.log(s)) // prints 'abc'
```

The main place you’d use this is if you had a function that accepted a promise but you wanted the caller to be able to send a variable or a promise and have it behave the same:

```typescript
function getIDAndMakeAPICall(id: number | Promise<number>) {
  Promise.resolve(id)
  .then(id => makeAPICall(id))
}
```

### Promises: Manually creating promises to work legacy callbacks [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-manually-creating-promises-to-work-legacy-callbacks)

If you’re working with non-promise code that you want to integrate with, the most basic way is to create a promise yourself.

```javascript
const promisifiedLegacy = () => new Promise((resolve, reject) => {
  someOldLegacyCallback((err, result) => {
    if (err) return reject(err)
    resolve(result)
  })
})
```

What we do is call the Promise constructor which accepts a function with `resolve()` and `reject()` callbacks as parameters.

It’s not necessary to `return` the `reject(err)`. If you call `reject()` and then call `resolve()` it will be rejected and never resolved. In other words, calling `resolve()` after `reject()` does not cause `then()` to be run. The reason for returning after `reject()` is just to make it clear that’s the behavior. Also, the return result of a promise constructor function does nothing.

### Promises: `util.promisify` [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-utilpromisify)

It’s a common enough task to take a callback function and turn it into a promise like above that there is a built-in util that makes it easy.

```javascript
const {promisify} = require('util')

const promisifiedLegacy = promisify(someOldLegacyCallback)

promisifiedLegacy()
.then(() => /**/)
```

### Promises: Order of operations [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-order-of-operations)

This is a bit of an aside because in 99% of cases it simply does not matter. Still, in that 1% you might need to know the exact order things will be executed.

The promise constructor function will be called right away but the `resolve()` won’t execute `.then()` until the next tick of the event loop:

```javascript
new Promise(resolve => {
  console.log(1)
  resolve()
})
.then(() => console.log(3))
console.log(2)
```

### Promises: Manually creating promises to encapsulate logic [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-manually-creating-promises-to-encapsulate-logic)

Creating manual promises is something not limited to wrapping callback code like above. It’s actually something I find myself doing more and more as I get better with async in many different ways.

In particular it’s handy when I want to take some complex async logic and wrap it up into a tidy promise. For example, let’s say I have some kind of connection object I need to make a couple of calls to then return once it’s fully connected:

```typescript
const connect = () => new Promise<{api: API, user: User}>((resolve, reject) => {
  const api = new API()
  api.on('connect', () => {
    authenticate('myapitoken')
    .then(() => api.getUser())
    .then(user => resolve({api, user}))
    .catch(reject)
  })
  api.on('error', reject)
}
```

Essentially I can do whatever logic I want and call `resolve()` when it’s finally all done with whatever I want to return. `connect()` is a complex sequence of various calls but using it is as simple as:

```javascript
const {api, user} = await connect()
```

### Promises: A noop promise that just waits [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-a-noop-promise-that-just-waits)

I use this anytime I want to “sleep” in my code.

```javascript
function wait (ms) {
  if (!ms) ms = 1000
  return new Promise(resolve => {
    // we can use setTimeout()
    // a built-in JS function to call a function after 'ms' time
    setTimeout(() => {
      resolve()
    }, ms)
  })
}

// this shorthand is equivalent to above
const wait = (ms = 1000) => new Promise(resolve => setTimeout(resolve), ms)
```

It will wait for 1000ms by default. If you pass a number like `wait(2000)` that will change the duration.

> _Note: `setTimeout()` does not guarantee something will run at that time, it just gives a minimum time it will wait until starting. It will be picked up as soon as the event loop runs and the duration has passed. Generally, because JS is so full of async operations this isn’t a major issue in practice._

### Promises: Timing out a promise [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-timing-out-a-promise)

`Promise.race()` is kind of like `Promise.all()`. Both take an array of promises but while `.all()` completes when they’re all done, `.race()` completes when any 1 completes—frankly, the only time I’ve ever seen `Promise.race()` used is for timeouts.

```javascript
Promise.race([\
  fetch('https://jsonplaceholder.typicode.com/todos'),\
  wait(30000).then(() => { throw new Error('timeout') }),\
])
.then(() => /*only called if not timed out*/)
.catch(() => /*handle timeout, or API error*/)

// if we wanted to abstract a bit we could create a timeout() function
// to timeoutify any promise
const timeout = (promise, ms=1000) => Promise.race([\
  promise,\
  wait(ms).then(() => { throw new Error('timeout') }),\
])

timeout(fetch('https://jsonplaceholder.typicode.com/todos'))
.then(() => /*only called if not timed out*/)
.catch(() => /*handle timeout, or API error*/)
```

Hopefully this is an example where it’s becoming clear _why_ the fact that promise’s singlar guarantees are helpful: only ever 1 result OR 1 error—never both. That timeout will eventually throw that timeout error regardless, but it’s not going to propagate as the `Promise.race()` promise already resolved.

There are a couple of issues with this approach. If the timeout completes first, it isn’t actually going to stop the request. The request will continue to faithfully execute and resolve/reject its promise, then it will go nowhere as the `Promise.race()` promise already has been rejected. Or if the request completes first, we have a function hanging around throwing an ignored timeout error after some time. As already mentioned, this doesn’t cause anything to actually _happen_ but it does use up some resources.

If you have heavy usage and/or long timeouts, you’ll want to consider this and create cancel functions. This is much more complex and I wouldn’t do it unless you need it—the cost of complexity likely outweighs the performance benefits. Still, here it is:

```javascript
// first we need a cancellable wait
const wait = (ms = 1000) => {
  let timer
  const p = new Promise(resolve => {
    timer = setTimeout(resolve, ms)
  })
  return {p, cancel: () => clearInterval(timer)}
}

// now we need to make fetch() cancellable
const AbortController = require('abort-controller')
const fetchWithCancel = url => {
  const aborter = new AbortController()
  const p = fetch(url, {signal: aborter.signal})
  return {p, cancel: () => aborter.abort()}
}

const timeoutWithCancel = ({p, cancel}, ms=1000) => {
  const w = wait(ms)
  return Promise.race([\
    p,\
    w.p.then(() => { throw new Error('timeout') }),\
  ])
  .finally(() => {
    cancel()
    w.cancel()
  })
}
```

### Promises: Memoizing with promises [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-memoizing-with-promises)

If you call `.then()` on a resolved promise it will still be called with the existing value. Also, promises can be called multiple times. Using this behavior, we can use promises to memoize expensive operations.

```javascript
const p = someExpensiveOperationThatReturnsAPromise()
p.then(() => console.log('got it once'))
p.then(() => console.log('got it twice'))
```

Not so useful on its own, but a place I’ve found it really useful is when I want to lazy evaluate something inside a class:

```javascript
class MyClass {

  // this is a 'private field' in case the '#' is confusing
  #thatExpensiveThing

  get thatExpensiveThing() {
    if (!this.#thatExpensiveThing) {
      // this will only be called once the first time it is accessed
      // any callers before the operation completes will wait until it is done
      // callers after the operation is done (even if it was long ago) will get the result right away
      this.#thatExpensiveThing = someExpensiveOperationThatReturnsAPromise()
    }
    return this.#thatExpensiveThing
  }
}

let c = new MyClass()

c.thatExpensiveThing.then(expensiveThing => {/**/})
c.thatExpensiveThing.then(expensiveThing => {/**/})
```

### Promises: `.finally()` [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#promises-finally)

In addition to `.then()` and `.catch()` there is a less commonly used (but still handy!) method called `.finally()`. This runs regardless of whether the promise was resolved or rejected. It’s useful when you want to perform some side effect after the promise is done.

```javascript
fetch('https://jsonplaceholder.typicode.com/todos/1')
  .then(todos => /*handle todos*/)
  .catch(err => /*ruh roh*/)
  .finally(() => /*run some code*/)
```

`.finally()` does not have any parameters because you shouldn’t care whether it was successful or not. For a practical example, I used this in the timeout cancellation code:

```javascript
const timeoutWithCancel = ({p, cancel}, ms=1000) => {
  /*...*/
  /* before: with then/catch */
  .then(res => {
    cancel()
    w.cancel()
    return res // we need to ensure we propagate the result
  })
  .catch(err => {
    cancel()
    w.cancel()
    throw err // we need to ensure we propagate the error
  })

  /* after: with finally */
  .finally(res => {
    cancel()
    w.cancel()
    // no need to propagate anything!
  })
}
```

## async/await [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait)

async/await is a new syntax that cleans up the boilerplate with promises. It is _not_ a replacement for promises[5](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fn:5). It just lets you write cleaner code that looks much more like traditional code. It doesn’t work in all cases and sometimes you’ll have to use promises. That’s fine, don’t worry about having a mix—that’s what JS code _should_ look like.

That said I want to be clear that async/await is incredible and **well** worth your time to learn. Just because is doesn’t work in all cases doesn’t mean the rest of the time it won’t make your code squeaky clean.

### async/await: Creating `async` functions [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-creating-async-functions)

We can create normal or arrow async functions. Just creating one causes anything it returns to be wrapped in a promise. (In fact it can replace usages of `Promise.resolve()`)

```javascript
async function myasyncfunc() {
  return 123
}
myasyncfunc().then(n => /*do something with 123*/)

const myasyncfunc = async () => 123 // equivalent syntax
```

Of course, that’s not that interesting. What’s interesting is that inside an `async` function we can use the `await` keyword to “halt”[6](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fn:6) the function until the promise is resolved. (Outside an `async` function `await` is invalid and you’ll get a parsing error.)

```javascript
async function fetchTodos() {
  const result = await fetch('https://jsonplaceholder.typicode.com/todos')
  const todos = await result.json()
  return todos
}
fetchTodos().then(todos => /*do something with todos*/)

// of course because async functions can await on promises and because async
// functions return promises we can use them with each other
async function fetchFirstTodo() {
  const todos = await fetchTodos()
  const result = await fetch('https://jsonplaceholder.typicode.com/todos')

  // let's refactor this. We don't need to store a variable
  const todo = await result.json()
  return todo
  // instead we can just return directly
  return await result.json()
  // and because result.json() is returning a promise, we don't actually need to await
  // we can just return the promise and JS will automatically prevent any sort of
  // "nested promise" situation (there is no such thing, but novices often fear it)
  return result.json()
  // note that inside try/catch blocks you likely NEED to say `return await _promise_`
  // more on that next
}
```

**Very important:** Note that while an async function does “halt” until the promise resolves/rejects, what’s actually happening is the event loop moves on to other work. The code is not frozen and if you happen to be screwing with shared memory you can get some weird bugs. You really need to understand this and not just try slapping `await` on statements until you get the result you want.

### async/await: Errors [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-errors)

If a promise errors out it will bubble up an error to any try/catch handlers.

```javascript
async function fetchTodo() {
  try {
    const result = await fetch('https://jsonplaceholder.typicode.com/todos')
    const todos = await result.json()
    return todos
  } catch (err) {
    // do something with err
  }
}
```

> This is one of my favorite things about async/await because without we used to have to handle errors both in try/catch (for synchonous errors) and `.catch()` for async errors. try/catch inside async thankfully catches both classes now.

If you haven’t ran into this next bug yet, you **will** at some point. If you return a promise in a try/catch and do _not_`await` on it, it will be returned, the function will be done, and the catch handler will never be called.

```javascript
async function fetchTodo() {
  try {
    const result = await fetch('https://jsonplaceholder.typicode.com/todos')

    return await result.json() // good!
    return result.json()       // BAD! this won't be caught in the exception handler if it fails
  } catch (err) {
    // do something with err
  }
}
```

That’s probably the #1 gotcha I’ve seen developers hit with async/await.

### async/await: Catching a single promise [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-catching-a-single-promise)

Never forget we’re dealing with promises here. Sometimes you want to catch an error but just in 1 promise. We can do that a couple of ways—one (I think) obviously better:

```javascript
async function fetchTodo() {
  // obvious but verbose solution
  let result
  try {
    result = await fetch('https://jsonplaceholder.typicode.com/todos')
    // do something with result
  } catch (err) {
    // handle err
  }

  const foo = await someOtherTask()
}

async function fetchTodo() {
  // cleaner solution
  // we don't even have to split the variable declaration out in this case
  // it will just be undefined if it fails
  const result = await fetch('https://jsonplaceholder.typicode.com/todos').catch(err => /*handle err*/)

  const foo = await someOtherTask()
}
```

This is a great example of what I was talking about earlier where async/await is worse syntax than promises by themselves.

### async/await: `finally` [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-finally)

Like with promises, we can also use finally in our try/catch blocks. In addition to the obvious use case of making sure something is always called after a function/block ends, you can also use it if you ever want to call something after you return a value.

```javascript
async () => {
  let todos = []
  try {
    const result = await fetch('https://jsonplaceholder.typicode.com/todos')
    todos = await result.json()
    return todos
  } catch (err) {
    // do something with error
  } finally {
    console.log(`num_todos: ${todos.length}`)
  }
}
```

> I probably could come up with a less contrived example for this one. It’s more helpful than this particular example shows I think.

### async/await: Operations in series [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-operations-in-series)

Assume you have an array of data and need to call a function that takes a single datum and returns a promise. You want to execute over the array in series. Here is what I might’ve done before async/await.

```javascript
const updateItem = id => fetch(`https://jsonplaceholder.typicode.com/todos/${id}`)

const run = () => {
  const data = [1, 2, 3, 4, 5]

  const process = () => {
    const datum = data.pop()
    if (datum) updateItem(datum).then(process)
  }
}
```

This is a pretty ugly solution. There may be better ones but modifying the array in place and the recursive function all make this difficult to follow. async/await lets us do this much better:

```javascript
const run = async () => {
  const data = [1, 2, 3, 4, 5]

  for (const datum of data) {
    await updateItem(datum)
  }
}
```

### async/await: Operations in parallel [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-operations-in-parallel)

We can map the data array to an array of `updateItem()` promises to easily perform this in series.

```javascript
const run = async () => {
  const data = [1,2,3,4,5]
  const promises = data.map(updateItem)

  for (const p of promises) await p
}
```

It starts the promises one after another without waiting for resolve/reject then in the for loop we just wait until each one is finished—essentially just waiting until they’re all done.

There are a couple of other ways to do this:

```javascript
const run = async () => {
  const data = [1,2,3,4,5]

  // with Promise.all()
  await Promise.all(data.map(updateItem))

  // with Promise.all() by storing promises in an array
  // this is useful in cases where you are dynamically adding in promises
  // perhaps where promises themselves add more promises
  const promises = []
  for (const datum of data) {
    promises.push(updateItem(datum))
  }
  await Promise.all(promises)
}
```

### async/await: Semi-parallel tasks [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-semi-parallel-tasks)

I run into this kind of thing a ton when doing performance work. Often I have enough data to _start_ a task which returns some data that I’ll need later, but I don’t need to block on it for a while. This is really easy with async/await:

```javascript
const run = async () => {
  const id = await getUserID()
  const resultINeedLaterPromise = getFirstResult(id) // runs in parallel with doSomeWork()
  await doSomeWork()
  const result = await resultINeedLaterPromise
  await doSomeWorkWithResult(result)
}
```

### async/await: Sleep [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#asyncawait-sleep)

Again, remember we are using promises! We can use our `wait()` if we want to pause an async/await routine.

```javascript
const wait = (ms = 1000) => new Promise(resolve => setTimeout(resolve), ms)

const run = async () => {
  console.log('started')
  await wait() // pause for 1000ms between console.log's
  console.log('done')
}
```

## Async Iterables [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables)

Async iterables are used when you have multiple promises coming in as a stream. It could be partial results or just watching some events. For example, you might have one that returns a file line-by-line, or one that listens to a pubsub channel from somewhere.

If you’ve considered [RxJS](https://rxjs-dev.firebaseapp.com/), a lot of what can be done with that library can now be done in vanilla JS with async iterables.

### Async Iterables: Basic Example [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-basic-example)

The easiest way to create an async iterable is with an async generator.

```typescript
// "sink" is the term for the final stage in evented systems
async function sink() {
  for await (const user of getUsers()) {
    console.dir(user)
  }
}

async function* getUsers() {
  console.log('fetching user 1')
  yield await fetchUser(1)
  console.log('fetching user 2')
  yield await fetchUser(2)
  console.log('fetching user 3')
  yield await fetchUser(3)
}

async function fetchUser(id) {
  const rsp = await fetch(`https://myapi/users/${id}`)
  return rsp.json()
}
```

The `yield` and `for await` syntax should be clearer soon. For now, look at the output of this code:

```txt
fetching user 1
{ id: 1, ... }
fetching user 2
{ id: 2, ... }
fetching user 3
{ id: 3, ... }
```

I point this out to show that `getUsers()` is not executed from beginning to end: it stops at each `yield`, makes the API call, returns the value to `sink()`, then `sink()` requests more data from `getUsers()` when it repeats the `for await...of` loop.

### Async Iterables: Log Server Example [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-log-server-example)

Let’s use a more practical example we can build off of. Assume we’re working on a system that is going to consume logs from a remote API. Here is the initial implementation:

```typescript
async function sink() {
  const logStream = logFetcher()
  for await (const logs of logStream) {
    console.dir(logs)
  }
}

// reads logs one at a time from server
async function* logFetcher(): AsyncGenerator<string[]> {
  while(true) {
    yield fetchLogs()
  }
}

// fetches next batch of logs from API
async function fetchLogs(): Promise<string[]> {
  const response = await fetch('https://myapi/get_logs')
  return response.json()
}
```

If you’d like to follow along with your own code, it’s useful to create a mock version of `logFetcher()` with some static content:

```typescript
async function* logFetcher(): AsyncGenerator<string[]> {
  const routes = ['/', '/categories/toys', '/categories/hiking']
  let id = 1
  for (let i=0; i<5; i++) {
    const logs = []
    for (let j=0; j<i%3+1; j++) {
      logs.push(`${id++} ${routes[i % routes.length]}`)
    }
    yield logs
  }
}
```

### Async Iterables: Transforms [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-transforms)

The first issue to tackle with our log reader is that the API returns an array of strings but we’d like to operate on each log entry at a time.

We could modify the API generator or `sink()` to traverse the array but the cleaner way is to add a transformer between the API and when `sink()` pulls the data out.

```typescript
async function sink() {
  const logStream = flatten(logFetcher())

  for await (const log of logStream) {
    console.dir(log)
  }
}

async function* flatten<T>(arrStream: AsyncIterable<T[]>): AsyncIterable<T> {
  for await (const arr of arrStream) {
    for (const x of arr) {
      yield x
    }
  }
}
```

The benefit to writing code in this way is it separates the logic of processing the stream from the business rules of how they’re applied. It allows us to reuse `flatten()` if we need the same logic somewhere else. It also allows us to write a simple unit test that is free from the rest of the system.

### Async Iterables: Testing Transform [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-testing-transform)

Here is a test of `flatten()` from the last section:

```typescript
// this pulls all the data out of the iterable into an array
// arrays are simply easier to validate in tests
const collect = async <T>(iter: AsyncIterable<T>): Promise<T[]> => {
  const o = []
  for await (const x of iter) o.push(x)
  return o
}

test('flatten', async () => {
  // our mock input to flatten()
  const source = async function*() {
    yield [1,2]
    yield [3]
    yield [4,5,6]
  }
  // call flatten()
  const output = flatten(source())
  // assert the output is valid
  expect(await collect(output)).toEqual([1,2,3,4,5,6])
})
```

All great tests should have these 3 (and only 3) parts: build input, execute logic, verify result.

### Async Iterables: Buffering [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-buffering)

One great thing about async iterables is how they won’t read more data in until the current data has been consumed. This is also known as backpressure. Say we had an iterator that was reading in a massive file—one too big to fit into memory. If the iterator kept on reading and filling a buffer up before we could process the data, we’d OOM.

One downside of this is that we’re always switching from reading to writing. Ideally we could read a few elements into a buffer so the consumer would have them ready for processing. Then we could asynchronously fetch more to keep filling the buffer as it’s being consumed.

Let’s say we want to have a 3-log buffer. Unfortunately it’s not possible to use `for await...of` here to consume the input iterable so we need to interact with the generator manually. First we fetch the iterator out of the iterable with `Symbol.asyncIterator`. Then we can call `.next()` on the iterator to fetch the next element.

```javascript
async function* buffer<T>(input: AsyncIterable<T>, size=1): AsyncGenerator<T> {
  const iter = input[Symbol.asyncIterator]()

  // initialize the buffer
  const buffer = []
  for(let i=0; i<size; i++) {
    buffer.push(iter.next())
  }
  for await (const {done, value} of buffer) {
    if (done) return // input is closed so close the output iterable too
    yield value // emit this value to consumer

    // we've consumed one so add another to the end of the buffer
    buffer.push(iter.next())
  }
}
```

> [`Symbol.asyncIterator`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for-await...of) is how an object declares it is an iterable. Calling it as a function on an object returns its iterator. In fact, this is what `for await...of` calls under the hood. We simply define a function with that symbol as a name and provide what the input stream returns while also calling the tap function.

Using `buffer()` works just like other transforms. Wrapping an iterable in `buffer()` will simply cause it to prefetch a few elements before the consumer asks for it.

### Async Iterables: `tap(fn)` [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-tapfn)

The `async function*` syntax is actually a helper in the same way that async/await is a helper for promises. Sometimes you’ll need to create async generators manually. Here is `tap()` which allows you to specify a function to be run for every element—useful for debugging/logging/monitoring. It is implemented as a generator and manual async iterable. They should be the same when executed.

```javascript
// async iterable as generator
async function* tap(input, fn) {
  for await (const x of input) {
    await fn(x)
    yield x
  }
}

// manually created async iterable
const tap = (input, fn) => ({
  [Symbol.asyncIterator]() {
    const iter = input[Symbol.asyncIterator]()
    return {
      async next() {
        const x = await iter.next()
        if (!x.done) fn(x.value)
        return x
      }
    }
  }
})
```

### Async Iterables: `clone()` [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-clone)

Out of the box, async iterables only send their output to a single consumer. We can, however, write a `clone()` middleware to allow n consumers to view the same data.

For example, imagine we have our log outputter and we want to have 2 different sinks: one looking for only `/categories/:category` requests and the other looking at all requests.

```typescript
async function sink() {
  let [allRoutes, categoryRoutes] = clone(flatten(logFetcher()), 2)
  categoryRoutes = filterRoutes(categoryRoutes, ' /categories/')

  await Promise.all([\
    processRoutes('/', allRoutes),\
    processRoutes('/categories', categoryRoutes),\
  ])
}

async function* filterRoutes(routes: AsyncIterable<string>, filter: string): AsyncIterable<string> {
  for await (const route of routes) {
    if (!route.includes(filter)) continue
    yield route
  }
}

const processRoutes = async (type: string, routes: AsyncIterable<string>) => {
  for await (const route of routes) {
    console.dir({type, route})
  }
}

const clone = <T>(input: AsyncIterable<T>, n=2): AsyncIterable<T>[] => {
  const iter = input[Symbol.asyncIterator]()
  const buffers = []

  // get the next element for 1 child
  // store the element in all the other buffers so it can be read by the others
  const next = (buffer) => {
    const x = iter.next()
    for (let b of buffers) {
      if (b === buffer) continue
      b.push(x)
    }
    return x
  }

  const childs = []
  for (let i=0; i<n; i++) {
    const buffer = []
    buffers.push(buffer)
    childs[i] = {
      [Symbol.asyncIterator]() {
        return {
          // reads from buffer if it has anything, otherwise fetches next element
          next: () => buffer.shift() || next(buffer)
        }
      }
    }
  }
  return childs
}
```

This is some fairly efficient architecture. The work before the clone is the same for all listeners so each iterable is processed once for both. Also, it won’t bother fetching more data from the upstream iterable until one of the consumers needs it. We didn’t have to write this logic, it works the way we want by default.

### Async Iterables: Reading Node Streams [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-reading-node-streams)

Node [streams](https://nodejs.org/api/stream.html) are actually async iterables themselves. We can use `fs.createReadStream()` and the [`for await...of`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for-await...of) syntax to read a file:

```javascript
async function sink() {
  // creates a node stream that reads a file in
  const fstream = fs.createReadStream('some_file.txt')
  fstream.setEncoding('utf8') // need this to not read as binary

  for await (const data of fstream) {
    console.dir(data)
  }
}
```

Out of the box this is going to read in large chunks of the file. If we instead wanted to have our sink just take in the file line-by-line, we could write a simple transform:

```javascript
const byLine = function* (input) {
  for await (const data of input) {
    for (const line of data.split('\n')) {
      yield line
    }
  }
}

// usage
const fstream = fs.createReadStream('some_file.txt')
fstream.setEncoding('utf8') // need this to not read as binary

for await (const line of byLine(fstream)) {
  console.dir(line)
}
```

### Async Iterables: Creating Node Readable Streams [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-creating-node-readable-streams)

As well as reading out readable streams, we can also create Node streams out of an async iterable:

```typescript
const { Readable } = require('stream')

async function * generate() {
  yield 'a'
  yield 'b'
  yield 'c'
}

const readable = Readable.from(generate())

readable.on('data', chunk => {
  console.dir(chunk)
})
```

If you need to interface with legacy code that accepts a readable stream this might come in handy.

### Async Iterables: Writing to Node Streams [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-writing-to-node-streams)

Writing to node streams is a bit more involved. There isn’t a direct way to do it like with reading. You need to create a readable stream from the async iterable and pipe that to a writer:

```typescript
const fs = require('fs')
const stream = require('stream')
const pipeline = util.promisify(stream.pipeline)

async function write(iter: AsyncIterable>) {
  const readable = stream.Readable.from(iter)
  const writable = fs.createWriteStream('file.out')
  await pipeline(readable, writable)
}
```

### Async Iterables: Error Handling [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-error-handling)

There are 2 places errors can occur while processing an async iterable. Either inside the iterable, or inside the sink. If an error occurs inside the sink there is nothing special about catching it in order to continuing processing later elements:

```typescript
async function sink() {
  for await (const log of getLogs()) {
    try {
      await process()
    } catch (err) {
      // handle err
    }
  }
}
```

However if an error occurs in side the iterator itself, say when a web request fails, it wouldn’t be safe to continue processing and there isn’t a way to do it from the sink. All you can do at the sink level is trap the error outside the loop:

```typescript
async function sink() {
  try {
    for await (const log of getLogs()) {
      await process()
    }
  } catch (err) {
    // handle err
  }
}
```

This means your program will likely exit which might not be what you want to happen for just a single HTTP error. You could call the sink again, but the better solution would be to add some retry logic inside the iterable:

```typescript
async function* getLogs(maxRetries = 10) {
  let retries = 0
  while(1) {
    try {
      yield await getLogsFromAPI()
      retries = 0 // reset retry count on success
    } catch (err) {
      if (retries > maxRetries) throw err
      await wait(2000 ** retries++) // exponential backoff
    }
  }
}
```

This way if it fails it will just wait a few seconds and try again unless it fails a bunch of times, in which case it will finally raise the exception.

### Async Iterables: Communicating with iterable [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#async-iterables-communicating-with-iterable)

Sometimes you need to send information to a running iterable from a sink (or downstream iterable). If we’re interacting with the iterable manually (not in a `for await...of` loop) then we can pass parameters to `iter.next(v)`. They can be accessed as return values like `const response = yield`.

Given we usually use `for await...of` that won’t work in most cases though. I feel there the best way is just to return an extra function that can be used as a backchannel:

```typescript
async function sink() {
  const nums = getNums()
  for await (const n of nums) {
    // stop when we get to 100
    if (n === 100) nums.cancel()
    console.dir(n)
  }
}

const getNums = () => {
  let stop = false
  const iter = (async function* () {
    let i = 0
    while (!stop) yield i++
  })()
  return {...iter, cancel: () => stop = true}
}
```

## Footnotes [\#](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/\#footnotes)

* * *

1. I really mean that. The number of people writing synchronous JS is negligible. [↩︎](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fnref:1)

2. I say “thread” but in Node there is only one thread (unless you’re doing some very nonstandard Node) which is the current process. [↩︎](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fnref:2)

3. Unless you’re working with legacy callback code [↩︎](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fnref:3)

4. In this example at least. Returning the promise is important in order to propagate errors up though. [↩︎](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fnref:4)

5. I called this out because people sometimes get confused because you can say you’re using promises OR async/await, meaning are you using the old promise _syntax_ or the new async/await syntax. They both use promises. [↩︎](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fnref:5)

6. “halt” in scarequotes because the JS event loops moves on and dispatches other tasks. A true “halt” would stop everything. That is never done in JS and there isn’t even a `Thread.sleep()` to do it, save for some third-party hacks. [↩︎](https://jdx.dev/posts/2020-01-19-async-javascript-patterns-for-2020/#fnref:6)