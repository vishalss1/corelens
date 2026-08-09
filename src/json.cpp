#include "corelens/model.hpp"
#include <cmath>
#include <iomanip>
#include <sstream>

namespace corelens {
std::string json_string(const std::string& value) {
    std::ostringstream s;
    s << '"';
    for (unsigned char c : value) {
        switch (c) {
        case '"': s << "\\""; break;
        case '\': s << "\\"; break;
        case '\n': s << "\n"; break;
        case '\r': s << "\r"; break;
        case '\t': s << "\t"; break;
        default:
            // Escape non-ASCII bytes too: output remains valid JSON for arbitrary binary stdout.
            if (c < 32 || c >= 127) s << "\u00" << std::hex << std::setw(2) << std::setfill('0') << int(c) << std::dec;
            else s << c;
        }
    }
    s << '"';
    return s.str();
}
static std::string number(std::optional<double> n) {
    if (!n || !std::isfinite(*n)) return "null";
    std::ostringstream s; s << std::setprecision(17) << *n; return s.str();
}
std::string profile_json(const Profile& p) {
    std::ostringstream s;
    s << "{\"schema_version\":1,\"elapsed_seconds\":" << number(p.process.elapsed_seconds)
      << ",\"exit_code\":" << p.process.exit_code
      << ",\"timed_out\":" << (p.process.timed_out ? "true" : "false")
      << ",\"output_truncated\":" << (p.process.output_truncated ? "true" : "false")
      << ",\"stdout\":" << json_string(p.process.out) << ",\"stderr\":" << json_string(p.process.err)
      << ",\"counter_error\":" << json_string(p.counter_error) << ",\"counters\":{";
    bool first = true;
    for (const auto& [name, c] : p.counters) {
        if (!first) s << ',';
        first = false;
        s << json_string(name) << ":{\"value\":" << number(c.value)
          << ",\"status\":" << json_string(c.status)
          << ",\"running_percent\":" << number(c.running_percent) << '}';
    }
    s << "},\"derived\":{"; first = true;
    for (const auto& [name, n] : p.derived) {
        if (!first) s << ',';
        first = false; s << json_string(name) << ':' << number(n);
    }
    s << "}}"; return s.str();
}
std::string assembly_json(const std::vector<Function>& functions, const std::vector<Finding>& findings) {
    std::ostringstream s; s << "{\"schema_version\":1,\"functions\":[";
    bool first = true;
    for (const auto& f : functions) {
        if (!first) s << ',';
        first = false;
        s << "{\"name\":" << json_string(f.name) << ",\"instruction_count\":" << f.instructions.size() << '}';
    }
    s << "],\"findings\":["; first = true;
    for (const auto& f : findings) {
        if (!first) s << ',';
        first = false;
        s << "{\"function\":" << json_string(f.function) << ",\"kind\":" << json_string(f.kind)
          << ",\"count\":" << f.count << ",\"explanation\":" << json_string(f.explanation)
          << ",\"experiment\":" << json_string(f.experiment) << '}';
    }
    s << "]}"; return s.str();
}
}
