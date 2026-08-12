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
