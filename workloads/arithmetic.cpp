#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>

static std::uint64_t kernel(std::uint64_t n) {
    std::uint64_t sum = 0;
    for (std::uint64_t i = 1; i <= n; ++i) {
        // Unsigned wrapping is defined; quotient/remainder invite strength reduction.
        sum += (i * 2654435761ULL) / 7 + (i % 31);
    }
    return sum;
}
int main(int argc, char** argv) {
    try {
        auto n = argc > 1 ? std::stoull(argv[1]) : 10000000ULL;
        if (!n || n > 1000000000ULL) throw std::invalid_argument("n must be 1..1000000000");
        std::cout << kernel(n) << '\n';
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
