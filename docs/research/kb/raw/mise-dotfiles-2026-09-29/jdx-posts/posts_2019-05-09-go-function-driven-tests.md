[Skip to content](https://jdx.dev/posts/2019-05-09-go-function-driven-tests/#main)

[Dave Cheney had a fantastic post on improving test structure in Go code with table-driven tests.](https://dave.cheney.net/2019/05/07/prefer-table-driven-tests) I want to expand on it just a tiny bit to show how table-driven tests can be made more concise with functions.

If you haven’t read his article, read that before continuing.

The end result of Dave’s post is the following example:

```go
func TestSplit(t *testing.T) {
    tests := map[string]struct {
        input string
        sep   string
        want  []string
    }{
        "simple":       {input: "a/b/c", sep: "/", want: []string{"a", "b", "c"}},
        "wrong sep":    {input: "a/b/c", sep: ",", want: []string{"a/b/c"}},
        "no sep":       {input: "abc", sep: "/", want: []string{"abc"}},
        "trailing sep": {input: "a/b/c/", sep: "/", want: []string{"a", "b", "c"}},
    }

    for name, tc := range tests {
        got := Split(tc.input, tc.sep)
        if !reflect.DeepEqual(tc.want, got) {
            t.Fatalf("%s: expected: %v, got: %v", name, tc.want, got)
        }
    }
}
```

This is a nice way to reduce code duplication, but closing over a new function we can go one step further:

```go
func TestSplit(t *testing.T) {
	test := func(name, input, sep string, want []string) {
		t.Run(name, func(t *testing.T) {
			got := Split(input, sep)
			diff := cmp.Diff(want, got)
			if diff != "" {
				t.Fatalf(diff)
			}
		})
	}

	test("simple", "a/b/c", "/", []string{"a", "b", "c"})
	test("wrong sep", "a/b/c", ",", []string{"a/b/c"})
	test("no sep", "abc", "/", []string{"abc"})
	test("trailing sep", "a/b/c/", "/", []string{"a", "b", "c", ""})
}
```