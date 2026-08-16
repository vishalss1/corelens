#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

int main(int argc, char** argv) {
    try {
        size_t n = argc > 1 ? std::stoull(argv[1]) : 2000000;
        if (!n || n > 20000000) throw std::invalid_argument("n must be 1..20000000");
        std::vector<std::uint32_t> a(n), b(n), c(n);
        for (size_t i = 0; i < n; ++i) { a[i] = i % 997; b[i] = i % 31; }
        for (unsigned repeat = 0; repeat < 32; ++repeat)
            for (size_t i = 0; i < n; ++i) c[i] = a[i] * 3 + b[i] + repeat;
        std::uint64_t checksum = 0;
        for (auto value : c) checksum += value;
        std::cout << checksum << '\n';
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
