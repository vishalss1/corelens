#include "corelens/model.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <thread>

void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
int main(int argc, char** argv) {
    if (argc > 1) {
        std::string mode = argv[1];
        if (mode == "echo") {
            for (int i = 2; i < argc; ++i) std::cout << argv[i] << '\n';
            std::cerr << "diagnostic\n"; return 7;
        }
        if (mode == "sleep") { std::this_thread::sleep_for(std::chrono::seconds(5)); return 0; }
        if (mode == "flood") {
            std::string chunk(8192, 'x');
            for (int i = 0; i < 640; ++i) { std::cout << chunk; std::cerr << chunk; }
            return 0;
        }
    }
    try {
        auto counters = corelens::parse_perf(
            "# header\n100;;cycles;1000;75.00;;\n200;;instructions;1000;75.00;;\n"
            "<not supported>;;cache-misses;0;0;;\n<not counted>;;branches;0;0;;\n"
            "nan;;branch-misses;0;0;;\n");
        check(counters.at("cycles").value == 100, "cycles parsing");
        check(counters.at("cycles").running_percent == 75, "multiplex percentage");
        check(counters.at("cache-misses").status == "unsupported", "unsupported event state");
        check(counters.at("branches").status == "not_counted", "not counted event state");
        check(!counters.at("branch-misses").value, "non-finite counters rejected");
        check(corelens::derive_metrics(counters).at("ipc") == 2, "IPC calculation");
        counters["cycles"].value = 0;
        check(!corelens::derive_metrics(counters).at("ipc"), "zero denominator");
        check(corelens::parse_perf("  5 ;; cycles:u ;10;99\n").at("cycles").value == 5, "whitespace and modifiers");
        check(corelens::json_string("\"\\\n\t\r") == "\"\\\"\\\\\\n\\t\\r\"", "JSON escapes");
        check(corelens::json_string(std::string(1, char(255))) == "\"\\u00ff\"", "binary output JSON encoding");
        auto functions = corelens::parse_assembly(
            "0000000000001000 <work(int)>:\n 1000: idivq %rcx\n 1004: jne 0x1000 <work(int)>\n"
            "0000000000002000 <arm>:\n 2000: sdiv x0, x1, x2\n");
        check(functions.size() == 2 && functions[0].instructions.size() == 2, "assembly grouping");
        auto findings = corelens::analyze_assembly(functions);
        check(findings.size() == 2 && findings[0].kind == "division", "division analysis on two architectures");
        auto child = corelens::run_process({argv[0], "echo", "two words", "quote\"inside", "trailing\\", ""}, 10);
        check(child.exit_code == 7, "child exit status");
        // Windows iostream converts newlines to CRLF; normalize for this protocol check.
        std::string normalized;
        for (char c : child.out) if (c != '\r') normalized += c;
        check(normalized == "two words\nquote\"inside\ntrailing\\\n\n", "argument quoting");
        check(child.err.find("diagnostic") != std::string::npos, "stderr capture");
        auto timeout = corelens::run_process({argv[0], "sleep"}, .05);
        check(timeout.timed_out && timeout.exit_code != 0 && timeout.elapsed_seconds < 2, "process deadline");
        auto flood = corelens::run_process({argv[0], "flood"}, 10);
        check(flood.output_truncated && flood.out.size() == 4 * 1024 * 1024 && flood.err.size() == 4 * 1024 * 1024,
              "bounded dual-pipe output without deadlock");
        std::cout << "All native regression checks passed\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
