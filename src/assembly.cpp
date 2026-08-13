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

namespace corelens {
std::vector<Finding> analyze_assembly(const std::vector<Function>& functions) {
    std::vector<Finding> result;
    const std::regex divisions(R"(^(i?div[bwlq]?|[su]div|[v]?divs[sd]|fdiv)$)");
    const std::regex branches(R"(^(j(?!mp)[a-z]+|b\.[a-z]+|cbn?z|tbn?z)$)");
    const std::regex calls(R"(^(call[q]?|bl|blr)$)");
    const std::regex scalar(R"(^(v?(add|mul|sub|div)s[sd]|f(add|mul|sub|div))$)");
    for (const auto& f : functions) {
        unsigned div = 0, branch = 0, call = 0, stack = 0, fp = 0;
        for (const auto& i : f.instructions) {
            if (std::regex_match(i.mnemonic, divisions)) ++div;
            if (std::regex_match(i.mnemonic, branches)) ++branch;
            if (std::regex_match(i.mnemonic, calls)) ++call;
            if (std::regex_match(i.mnemonic, scalar)) ++fp;
            if (i.operands.find("(%rsp)") != std::string::npos || i.operands.find("(%rbp)") != std::string::npos ||
                i.operands.find("[sp") != std::string::npos) ++stack;
        }
        auto add = [&](std::string kind, unsigned count, std::string why, std::string experiment) {
            result.push_back({f.name, std::move(kind), std::move(why), std::move(experiment), count});
        };
        if (div) add("division", div, "Division instructions can have high latency if this function is hot.", "Try loop invariant hoisting or constant divisors; validate arithmetic semantics and benchmark.");
        if (branch >= 4) add("branch_density", branch, "Many conditional branch sites; static counts cannot predict misprediction rates.", "Measure branch-misses; compare data ordering or a branchless implementation.");
        if (call >= 4) add("call_density", call, "Many call sites may add overhead in a hot function.", "Compare -O2 and -O3, inspect inline remarks, and try LTO.");
        if (stack >= 8) add("stack_traffic", stack, "Frequent stack operands may reflect spills, locals, or intentional stack access.", "Compare optimized assembly; reduce live temporaries only if cycles improve.");
        if (fp >= 4) add("scalar_floating_point", fp, "Scalar floating point sites may be vectorization candidates; dependencies may prevent this.", "Inspect LLVM loop vectorization remarks and aliasing; avoid fast-math unless semantics permit.");
    }
    return result;
}
}
