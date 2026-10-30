// p2996 verify compiles and runs this with clang++-p2996 and expects "reflection value=43".
#include <iostream>
#include <meta>
#include <stdexcept>
#include <string>
#include <type_traits>

struct Record { int value; };
constexpr auto member = std::meta::nonstatic_data_members_of(
    ^^Record, std::meta::access_context::current())[0];
static_assert(std::meta::identifier_of(member) == "value");
static_assert(std::is_same_v<typename [:std::meta::type_of(member):], int>);

int main() {
    Record record{42};
    record.[:member:] += 1;
    try {  // exercises libc++abi and libunwind from the default config
        throw std::runtime_error("reflection value=" + std::to_string(record.[:member:]));
    } catch (const std::exception& error) {
        std::cout << error.what() << '\n';
    }
    return record.value == 43 ? 0 : 1;
}
