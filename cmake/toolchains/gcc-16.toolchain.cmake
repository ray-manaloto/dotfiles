# GCC 16. The list form puts the flags on every compile, link and try_compile line, whatever a
# target sets; a later -std from the caller or project wins. Change the list only with cmake --fresh.
set(CMAKE_C_COMPILER gcc-16)
set(CMAKE_CXX_COMPILER g++-16 -std=c++26 -freflection)
