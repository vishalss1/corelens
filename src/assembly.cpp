#include "corelens/model.hpp"
#include <filesystem>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace corelens {
std::vector<Function> disassemble(const std::string& binary, const std::string& objdump) {
    if (!std::filesystem::is_regular_file(binary)) throw std::invalid_argument("binary does not exist: " + binary);
    auto result = run_process({objdump, "--disassemble", "--demangle", "--no-show-raw-insn", std::filesystem::absolute(binary).string()}, 60);
    if (result.exit_code != 0 || result.timed_out) throw std::runtime_error("LLVM disassembly failed: " + result.err);
    if (result.output_truncated) throw std::runtime_error("disassembly exceeds the 4 MiB capture limit");
    auto functions = parse_assembly(result.out);
    if (functions.empty()) throw std::runtime_error("no decoded instructions found in binary");
    return functions;
}
}

namespace corelens {
std::vector<Function> parse_assembly(const std::string& text) {
    std::regex symbol(R"(^\s*[0-9a-fA-F]+\s+<(.+)>:\s*$)");
    std::regex instruction(R"(^\s*([0-9a-fA-F]+):\s+([a-zA-Z][a-zA-Z0-9_.]*)\s*(.*)$)");
    std::vector<Function> functions;
    std::istringstream input(text); std::string line; std::smatch match;
    while (std::getline(input, line)) {
        if (std::regex_match(line, match, symbol)) functions.push_back({match[1].str(), {}});
        else if (std::regex_match(line, match, instruction)) {
            if (functions.empty()) functions.push_back({"<unknown>", {}});
            functions.back().instructions.push_back({match[1].str(), match[2].str(), match[3].str()});
        }
    }
    return functions;
}
}
