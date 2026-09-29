[Skip to content](https://mise.jdx.dev/mise-cookbook/cpp.html#VPContent)

On this page

# C++ Cookbook [​](https://mise.jdx.dev/mise-cookbook/cpp.html\#c-cookbook)

Use mise to install build tools and define the configure/build cycle. A C or C++ compiler must already be available, for example through your operating system's development tools. Installing CMake does not install a compiler.

## A C++ Project with CMake [​](https://mise.jdx.dev/mise-cookbook/cpp.html\#a-c-project-with-cmake)

This recipe expects a `CMakeLists.txt` at the project root. It uses CMake's build interface so the task does not depend on a specific Make or Ninja generator:

mise.toml

toml

```
[tools]
cmake = "latest"

[tasks.configure]
description = "Configure the CMake build"
run = 'cmake -S . -B build'

[tasks.build]
description = "Build the project"
alias = "b"
depends = ["configure"]
run = 'cmake --build build'

[tasks.clean]
description = "Clean compiled targets while keeping CMake configuration"
alias = "c"
run = 'cmake --build build --target clean'
```

Run `mise run build` from the project. It configures the build directory before compiling. After the first build, `mise run clean` removes compiled targets using the selected generator's clean target; it keeps the build configuration.

For a runnable example, create these two files:

CMakeLists.txt

cmake

```
cmake_minimum_required(VERSION 3.20)
project(hello LANGUAGES CXX)
add_executable(hello main.cpp)
```

main.cpp

cpp

```
#include <iostream>

int main() {
    std::cout << "Hello from CMake\n";
}
```

With a single-configuration generator such as Unix Makefiles, the resulting program is `build/hello` on Unix. Multi-configuration generators can put it in a configuration subdirectory; build a specific configuration with `mise run build -- --config Debug` and use that generator's output path.

Add `build/` to `.gitignore`. See [CMake's command-line reference](https://cmake.org/cmake/help/latest/manual/cmake.1.html) for generator selection and build options.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)