#include "greet.hpp"

#include <format>

std::string greet(std::string_view name) { return std::format("hello {}", name); }
