#pragma once
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace corelens {
struct ProcessResult {
    int exit_code = -1;
    double elapsed_seconds = 0;
    bool timed_out = false;
    bool output_truncated = false;
    std::string out, err;
};
struct Counter {
    std::optional<double> value;
    std::optional<double> running_percent;
    std::string status = "missing";
};
using Counters = std::map<std::string, Counter>;
struct Profile {
    ProcessResult process;
    Counters counters;
    std::map<std::string, std::optional<double>> derived;
    std::string counter_error;
};
struct Instruction {
    std::string address, mnemonic, operands;
};
struct Function {
    std::string name;
    std::vector<Instruction> instructions;
};
struct Finding {
    std::string function, kind, explanation, experiment;
    unsigned count = 0;
};
ProcessResult run_process(const std::vector<std::string>& args, double timeout_seconds = 30);
Counters parse_perf(const std::string& data);
std::map<std::string, std::optional<double>> derive_metrics(const Counters& counters);
Profile profile(const std::vector<std::string>& args, double timeout, bool use_perf);
std::vector<Function> parse_assembly(const std::string& text);
std::vector<Finding> analyze_assembly(const std::vector<Function>& functions);
std::vector<Function> disassemble(const std::string& binary, const std::string& objdump);
std::string json_string(const std::string& value);
std::string profile_json(const Profile& value);
std::string assembly_json(const std::vector<Function>& functions, const std::vector<Finding>& findings);
}
