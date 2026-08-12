#include "corelens/model.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

static double positive(const std::string& value) {
    size_t end; double n = std::stod(value, &end);
    if (end != value.size() || !std::isfinite(n) || n <= 0) throw std::invalid_argument("timeout must be finite and positive");
    return n;
}
int main(int argc, char** argv) {
    try {
        if (argc < 2 || std::string(argv[1]) == "--help") {
            std::cout << "CoreLens 0.1.0\nUsage:\n  corelens-native run [--perf] [--timeout SECONDS] -- PROGRAM [ARGS...]\n";
            return argc < 2 ? 2 : 0;
        }
        std::string command = argv[1];
        if (command == "--version") { std::cout << "0.1.0\n"; return 0; }
        if (command == "run") {
            bool perf = false; double timeout = 30; int i = 2;
            for (; i < argc && std::string(argv[i]) != "--"; ++i) {
                std::string option = argv[i];
                if (option == "--perf") perf = true;
                else if (option == "--timeout" && i + 1 < argc) timeout = positive(argv[++i]);
                else throw std::invalid_argument("unknown or incomplete option: " + option);
            }
            if (i == argc || ++i == argc) throw std::invalid_argument("provide a program after --");
            std::vector<std::string> args(argv + i, argv + argc);
            auto p = corelens::profile(args, timeout, perf);
            std::cout << corelens::profile_json(p) << '\n';
            return p.process.timed_out ? 124 : (p.process.exit_code == 0 ? 0 : 1);
        }
        throw std::invalid_argument("unknown command: " + command);
    } catch (const std::exception& e) {
        std::cerr << "{\"error\":" << corelens::json_string(e.what()) << "}\n"; return 2;
    }
}
