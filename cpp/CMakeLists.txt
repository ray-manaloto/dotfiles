cmake_minimum_required(VERSION 4.0)
project(dotfiles2_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 26)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(greet src/greet.cpp)
target_include_directories(greet PUBLIC src)

enable_testing()
add_executable(greet_test tests/greet_test.cpp)
target_link_libraries(greet_test PRIVATE greet)
add_test(NAME greet_test COMMAND greet_test)
