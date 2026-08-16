#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

int main(int argc, char** argv) {
    try {
        size_t n = argc > 1 ? std::stoull(argv[1]) : 2000000;
        bool sorted = argc > 2 && std::string(argv[2]) == "sorted";
        if (!n || n > 20000000) throw std::invalid_argument("n must be 1..20000000");
        std::vector<std::uint32_t> values(n); std::uint32_t state = 713;
        for (auto& v : values) { state = state * 1664525U + 1013904223U; v = state % 256; }
        if (sorted) std::sort(values.begin(), values.end());
        std::uint64_t sum = 0;
        for (unsigned repeat = 0; repeat < 32; ++repeat)
            for (auto value : values) if (value >= 128) sum += value;
        std::cout << sum << '\n';
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
