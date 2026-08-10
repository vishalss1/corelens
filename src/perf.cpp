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
    std::istringstream stream(data); std::string line;
    while (std::getline(stream, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::vector<std::string> fields; std::istringstream row(line); std::string field;
        while (std::getline(row, field, ';')) fields.push_back(trim(field));
        if (fields.size() < 3) continue;
        auto event = fields[2];
        auto modifier = event.find(':'); if (modifier != std::string::npos) event.resize(modifier);
        if (!result.count(event)) continue;
        Counter c;
        c.value = numeric(fields[0]);
        if (c.value) c.status = "ok";
        else if (fields[0].find("not supported") != std::string::npos) c.status = "unsupported";
        else if (fields[0].find("not counted") != std::string::npos) c.status = "not_counted";
        else c.status = "invalid";
        if (fields.size() >= 5) c.running_percent = numeric(fields[4]);
        result[event] = c;
    }
    return result;
}
}
