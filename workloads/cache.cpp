#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

int main(int argc, char** argv) {
    try {
        size_t side = argc > 1 ? std::stoull(argv[1]) : 1024;
        bool rows = argc > 2 && std::string(argv[2]) == "rows";
        if (!side || side > 8192) throw std::invalid_argument("side must be 1..8192");
        std::vector<std::uint32_t> matrix(side * side);
        for (size_t i = 0; i < matrix.size(); ++i) matrix[i] = i % 251;
        std::uint64_t sum = 0;
        for (unsigned repeat = 0; repeat < 16; ++repeat)
            for (size_t i = 0; i < side; ++i)
                for (size_t j = 0; j < side; ++j)
                    sum += matrix[rows ? i * side + j : j * side + i];
        std::cout << sum << '\n';
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
