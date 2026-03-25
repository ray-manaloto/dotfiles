#!/usr/bin/env bats

# python: Reachability and version check
@test "python: reachability" {
  run python3 --version
  [ "$status" -eq 0 ]
}

@test "python: version check" {
  run python3 --version
  [[ "$output" == *"Python 3."* ]]
}

# node: Reachability and version check
@test "node: reachability" {
  run node --version
  [ "$status" -eq 0 ]
}

@test "node: version check" {
  run node --version
  [[ "$output" == *"v"* ]]
}

# go: Reachability and version check
@test "go: reachability" {
  run go version
  [ "$status" -eq 0 ]
}

@test "go: version check" {
  run go version
  [[ "$output" == *"go version"* ]]
}

# rust: Reachability and version check (rustc and cargo)
@test "rustc: reachability" {
  run rustc --version
  [ "$status" -eq 0 ]
}

@test "rustc: version check" {
  run rustc --version
  [[ "$output" == *"rustc"* ]]
}

@test "cargo: reachability" {
  run cargo --version
  [ "$status" -eq 0 ]
}

@test "cargo: version check" {
  run cargo --version
  [[ "$output" == *"cargo"* ]]
}
