#include "corelens/model.hpp"
#include <algorithm>
#include <cmath>
#include <sstream>

namespace corelens {
static std::string trim(std::string s) {
    auto begin = s.find_first_not_of(" \t\r\n");
    if (begin == std::string::npos) return "";
    return s.substr(begin, s.find_last_not_of(" \t\r\n") - begin + 1);
}
static std::optional<double> numeric(const std::string& s) {
    try {
        size_t end = 0; double n = std::stod(s, &end);
        if (end == s.size() && std::isfinite(n) && n >= 0) return n;
    } catch (...) {}
    return std::nullopt;
}
Counters parse_perf(const std::string& data) {
    Counters result;
    for (const char* name : {"cycles", "instructions", "cache-references", "cache-misses", "branches", "branch-misses"}) result[name] = {};
    std::map<std::string, std::vector<Counter>> domains;
    std::istringstream stream(data); std::string line;
    while (std::getline(stream, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::vector<std::string> fields; std::istringstream row(line); std::string field;
        while (std::getline(row, field, ';')) fields.push_back(trim(field));
        if (fields.size() < 3) continue;
        auto event = fields[2];
        auto modifier = event.find(':'); if (modifier != std::string::npos) event.resize(modifier);
        std::string canonical = event;
        auto first_slash = event.find('/');
        if (first_slash != std::string::npos) {
            auto last_slash = event.find('/', first_slash + 1);
            if (last_slash == std::string::npos) continue;
            canonical = event.substr(first_slash + 1, last_slash - first_slash - 1);
        }
        if (!result.count(canonical)) continue;
        Counter c;
        c.value = numeric(fields[0]);
        if (c.value) c.status = "ok";
        else if (fields[0].find("not supported") != std::string::npos) c.status = "unsupported";
        else if (fields[0].find("not counted") != std::string::npos) c.status = "not_counted";
        else c.status = "invalid";
        if (fields.size() >= 5) c.running_percent = numeric(fields[4]);
        result[event] = c;
        if (canonical != event) domains[canonical].push_back(c);
    }
    for (const auto& [event, entries] : domains) {
        if (result[event].status != "missing") continue;
        Counter aggregate;
        aggregate.value = 0;
        aggregate.status = "ok";
        for (const auto& entry : entries) {
            if (!entry.value) { aggregate.value.reset(); aggregate.status = "partial"; }
            else if (aggregate.value) *aggregate.value += *entry.value;
            if (entry.running_percent && (!aggregate.running_percent || *entry.running_percent < *aggregate.running_percent))
                aggregate.running_percent = entry.running_percent;
        }
        result[event] = aggregate;
    }
    return result;
}
}

#include <filesystem>
#include <fstream>
#include <stdexcept>
#ifndef _WIN32
#include <unistd.h>
#endif
namespace corelens {
Profile profile(const std::vector<std::string>& args, double timeout, bool use_perf) {
    Profile p;
    p.counters = parse_perf("");
    if (!use_perf) {
        p.process = run_process(args, timeout);
        p.counter_error = "hardware counters were not requested";
        return p;
    }
#ifdef _WIN32
    throw std::runtime_error("Linux perf requires Linux; omit --perf for timing on Windows");
#else
    std::string path = (std::filesystem::temp_directory_path() / "corelens-perf-XXXXXX").string();
    std::vector<char> writable(path.begin(), path.end()); writable.push_back(0);
    int fd = mkstemp(writable.data());
    if (fd < 0) throw std::runtime_error("could not create perf result file");
    close(fd); path = writable.data();
    struct Cleanup { std::string path; ~Cleanup() { std::error_code e; std::filesystem::remove(path, e); } } cleanup{path};
    std::vector<std::string> command = {"perf", "stat", "--no-big-num", "-x", ";", "-e",
        "cycles,instructions,cache-references,cache-misses,branches,branch-misses", "-o", path, "--"};
    command.insert(command.end(), args.begin(), args.end());
    // perf's CSV numbers must be independent of the user's numeric locale.
    command.insert(command.begin(), {"env", "LC_ALL=C"});
    p.process = run_process(command, timeout);
    std::ifstream input(path); std::ostringstream content; content << input.rdbuf();
    p.counters = parse_perf(content.str());
    bool any = false;
    for (const auto& [name, c] : p.counters) { (void)name; if (c.value) any = true; }
    if (!any) p.counter_error = "perf returned no usable counters; inspect stderr, perf installation, event support, and perf_event_paranoid";
    p.derived = derive_metrics(p.counters);
    return p;
#endif
}
}

namespace corelens {
std::map<std::string, std::optional<double>> derive_metrics(const Counters& counters) {
    auto ratio = [&](const std::string& numerator, const std::string& denominator) -> std::optional<double> {
        auto n = counters.find(numerator), d = counters.find(denominator);
        if (n == counters.end() || d == counters.end() || !n->second.value || !d->second.value || *d->second.value <= 0) return std::nullopt;
        return *n->second.value / *d->second.value;
    };
    return {{"ipc", ratio("instructions", "cycles")},
            {"cache_miss_ratio", ratio("cache-misses", "cache-references")},
            {"branch_miss_ratio", ratio("branch-misses", "branches")}};
}
}
