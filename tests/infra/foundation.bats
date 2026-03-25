#!/usr/bin/env bats

# mise: Reachability and 'doctor' status
@test "mise: reachability" {
  run mise --version
  [ "$status" -eq 0 ]
}

@test "mise: doctor status" {
  run mise doctor
  [ "$status" -eq 0 ]
  [[ "$output" == *"activated: yes"* ]]
  [[ "$output" == *"shims_on_path: yes"* ]]
  [[ "$output" == *"No problems found"* ]]
}

# chezmoi: Reachability and root directory validation
@test "chezmoi: reachability" {
  run chezmoi --version
  [ "$status" -eq 0 ]
}

@test "chezmoi: root directory validation" {
  run chezmoi source-path
  [ "$status" -eq 0 ]
  [ -d "$output" ]
}

# uv: Reachability and python interpreter linking
@test "uv: reachability" {
  run uv --version
  [ "$status" -eq 0 ]
}

@test "uv: python interpreter linking" {
  run uv python find
  [ "$status" -eq 0 ]
  [ -x "$output" ]
}

# pixi: Reachability and self-check
@test "pixi: reachability" {
  run pixi --version
  [ "$status" -eq 0 ]
}

@test "pixi: self-check (info)" {
  run pixi info
  [ "$status" -eq 0 ]
  [[ "$output" == *"Pixi version:"* ]]
  [[ "$output" == *"Bin dir:"* ]]
}
