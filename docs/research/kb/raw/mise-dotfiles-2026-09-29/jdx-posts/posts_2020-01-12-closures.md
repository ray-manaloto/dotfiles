[Skip to content](https://jdx.dev/posts/2020-01-12-closures/#main)

On this page

> Closures are fairly common in JS but are also sometimes used in Go and Python and many other languages. This post is going to use JS but the concept is the same in all languages supporting closures.

I found closures incredibly confusing for a long time—well after college and me working in the industry for years in fact. I found the concept confusing even when I was writing them all the time.

The problem for me was not having a clear, real-world example to chew on.

The MDN guide for closures starts with this example:

```javascript
function init() {
  var name = 'Mozilla'; // name is a local variable created by init
  function displayName() { // displayName() is the inner function, a closure
    alert(name); // use variable declared in the parent function
  }
  displayName();
}
init();
```

I kind of get it. I creates a new function called `displayName()` where it has `'Mozilla'` prefilled, but how is that useful? Let’s take a more practical example[1](https://jdx.dev/posts/2020-01-12-closures/#fn:1).

## Function Dependencies [\#](https://jdx.dev/posts/2020-01-12-closures/\#function-dependencies)

This is probably the #1 way I use closures in my own code—for this exact problem to a ‘T’.

Imagine we have a function to get the current user in a backend. We have a postgres and redis connection. We use the redis connection to fetch the ID of the current user from a session key and a postgres connection for DB queries:

```javascript
function getUserFromDB(postgres, redis, sessionID) {
  const session = redis.getSession(sessionID)
  return postgres.query('SELECT * FROM users WHERE ID = ?', session.userID)
}
```

If we had a group of similar functions like `getUserFromDB()`, passing in the redis/pg connections each time would be annoying. As an example, imagine we had a request that looked like this:

```javascript
r.get('/messages', (req, res) => {
  const user = getUserFromDB(postgres, redis, sessionID)
  const notifications = getUserNotifications(postgres, redis, user.id)
  const profile = getUserProfile(postgres, redis, user.id)
})
```

Ideally we could just make those calls and not have to keep passing postgres/redis into them.

## Class Solution [\#](https://jdx.dev/posts/2020-01-12-closures/\#class-solution)

In a lot of languages, including JS, you can get by without closures. I think it’s important to see what problem they solve by first looking at the way we solve it _without_ closures.

We could use OO and create a class that keeps the DB connections inside of the class instance:

```javascript
// service code
class UserService {
  constructor (postgres, redis) {
    this.postgres = postgres
    this.redis = redis
  }

  getUserFromDB(sessionID) {
    const session = this.redis.getSession(sessionID)
    return this.postgres.query('SELECT * FROM users WHERE ID = ?', session.userID)
  }
}

// route code
const userSVC = new UserService(postgres, redis)

r.get('/messages', (req, res) => {
  const user = userSVC.getUserFromDB(sessionID)
})
```

## Closure Solution [\#](https://jdx.dev/posts/2020-01-12-closures/\#closure-solution)

Alternatively, we could use a closure to solve this problem instead. Let’s see the code and then discuss:

```javascript
// service code
function newGetUserFromDB(postgres, redis) {
  return function (sessionID) {
    const session = redis.getSession(sessionID)
    return postgres.query('SELECT * FROM users WHERE ID = ?', session.userID)
  }
}
// we could also use arrow functions to make this more concise
// it's the same as above
const newGetUserFromDB = (postgres, redis) => sessionID => {
    const session = redis.getSession(sessionID)
    return postgres.query('SELECT * FROM users WHERE ID = ?', session.userID)
}

// route code
const getUserFromDB = newGetUserFromDB(postgres, redis)

r.get('/messages', (req, res) => {
  const user = getUserFromDB(sessionID)
})
```

Essentially closures allow us to “save”[2](https://jdx.dev/posts/2020-01-12-closures/#fn:2) the postgres/redis variables into the function so that we don’t need to pass them when we call the function later.

## Closure w/ object [\#](https://jdx.dev/posts/2020-01-12-closures/\#closure-w-object)

Closures are a more basic solution to the problem. It’s less code than writing a class for a single function. Classes are nice though because it allows us to group a bunch of things together. We could do that with closures too by returning an object instead of a function:

```javascript
// service code
const userSVC = (postgres, redis) => {
  return {
    getUserFromDB: sessionID => {
      const session = redis.getSession(sessionID)
      return postgres.query('SELECT * FROM users WHERE ID = ?', session.userID)
    },
    getUserNotifications: userID => {},
    getUserProfile: userID => {},
  }
}

// route code
const svc = userSVC(postgres, redis)

r.get('/messages', (req, res) => {
  const user = svc.getUserFromDB(sessionID)
  const notifications = svc.getUserNotifications(user.id)
  const profile = svc.getUserProfile(user.id)
})
```

This ultimately isn’t much different from classes but one benefit is it completely hides the postgres and redis client from any code that uses it. In the class we might want to treat the properties as private properties which we can’t do[3](https://jdx.dev/posts/2020-01-12-closures/#fn:3).

## Are closures better? [\#](https://jdx.dev/posts/2020-01-12-closures/\#are-closures-better)

Not necessarily. I am pretty sure there isn’t a single thing that you can do in closures that couldn’t be done with classes in fact. They both are different ways of hiding inner variables.

Classes are more code than closures. Chiefly because they require a constructor function where closures do not. This isn’t a bad thing, a class clearly denotes to the reader of the code what is going on.

Closures on the other hand are more concise and make it easy to do more advanced things.

So they both solve the same problem but use classes when you want consistency and closures when you want flexibility.

## Advanced Closures: Profiling Example [\#](https://jdx.dev/posts/2020-01-12-closures/\#advanced-closures-profiling-example)

Let’s take a quick look at a couple of things you can do with closures that are more advanced. These also could be done with classes but they are getting to a point where the class syntax is more of a burden.

Imagine we want a profiling function that wraps a function (task) and returns the duration it took to run:

```javascript
const profile = (description, task) => () => {
  const start = new Date()
  const result = task()
  const end = new Date()
  console.log(`${description}: took ${end - start}ms to run`)
  return result
}
// inside the calling code
const getUserFromDB = profile('getUserFromDB', newGetUserFromDB(postgres, redis))

r.get('/messages', (req, res) => {
  const user = getUserFromDB(sessionID)
})
```

Now when we call `getUserFromDB()` we’ll see how long it took to execute.

Now let’s imagine we want those logging entries to be prefixed with the current route. We could modify `profile()` to include a `.prefix()` function that modifies the description of an existing profile closure and returns a new closure:

```javascript
const profile = (description, task) => {
  const closure = () => {
    const start = new Date()
    const result = task()
    const end = new Date()
    console.log(`${description}: took ${end - start}ms to run`)
    return result
  }
  closure.prefix = (prefix) => profile(`${description} ${prefix}`, task)
  return closure
}
// inside the calling code
const getUserFromDB = profile('getUserFromDB', newGetUserFromDB(postgres, redis))

r.get('/messages', (req, res) => {
  const getUserFromDB2 = getUserFromDB.prefix('/messages')
  const user = getUserFromDB2(sessionID)
})
```

What is nice here is we can call `prefix()` inside the route and we don’t have to also pass the description again.

You could solve this with classes. It would not be nearly as concise. That said, there is always an argument for simple solutions and maybe this is more complex than necessary.

## Footnotes [\#](https://jdx.dev/posts/2020-01-12-closures/\#footnotes)

* * *

1. The MDN article does have a “practical” example but IMO it’s not practical enough. [↩︎](https://jdx.dev/posts/2020-01-12-closures/#fnref:1)

2. Commonly we would say we “closed over” the db connections. [↩︎](https://jdx.dev/posts/2020-01-12-closures/#fnref:2)

3. This is historically accurate, but private fields are coming very soon so you will be able to have the same privacy with classes soon. [↩︎](https://jdx.dev/posts/2020-01-12-closures/#fnref:3)