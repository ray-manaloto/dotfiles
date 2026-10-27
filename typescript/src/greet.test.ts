import { expect, test } from "bun:test";
import { greet } from "./greet";

test("greet", () => {
  expect(greet("mods")).toBe("hello mods");
});
