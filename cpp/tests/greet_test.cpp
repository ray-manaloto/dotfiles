#include "greet.hpp"

#include <print>

int main() {
  if (greet("cpp") != "hello cpp") {
    std::println(stderr, "greet returned the wrong text");
    return 1;
  }
  std::println("greet ok, __cplusplus={}", __cplusplus);
  return 0;
}
