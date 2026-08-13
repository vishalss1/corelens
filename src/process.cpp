#include "corelens/model.hpp"
#include <chrono>
#include <stdexcept>
#include <thread>

namespace corelens {
static constexpr size_t output_limit = 4 * 1024 * 1024;
static void append_output(std::string& dest, const char* data, size_t size, ProcessResult& result) {
    size_t available = output_limit - dest.size();
    dest.append(data, size < available ? size : available);
    if (size > available) result.output_truncated = true;
}
}
#ifndef _WIN32
#include <cerrno>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <sys/wait.h>
#include <unistd.h>
namespace corelens {
ProcessResult run_process(const std::vector<std::string>& args, double timeout) {
    if (args.empty() || timeout <= 0) throw std::invalid_argument("command and positive timeout required");
    std::vector<char*> argv;
    for (const auto& a : args) argv.push_back(const_cast<char*>(a.c_str()));
    argv.push_back(nullptr);
    int outpipe[2], errpipe[2];
    if (pipe(outpipe)) throw std::runtime_error("stdout pipe failed");
    if (pipe(errpipe)) { close(outpipe[0]); close(outpipe[1]); throw std::runtime_error("stderr pipe failed"); }
    auto start = std::chrono::steady_clock::now();
    pid_t pid = fork();
    if (pid == -1) {
        for (int fd : {outpipe[0], outpipe[1], errpipe[0], errpipe[1]}) close(fd);
        throw std::runtime_error("fork failed");
    }
    if (pid == 0) {
        setpgid(0, 0);
        dup2(outpipe[1], STDOUT_FILENO); dup2(errpipe[1], STDERR_FILENO);
        for (int fd : {outpipe[0], outpipe[1], errpipe[0], errpipe[1]}) close(fd);
        execvp(argv[0], argv.data());
        const char message[] = "CoreLens: executable could not be started\n";
        write(STDERR_FILENO, message, sizeof(message) - 1);
        _exit(127);
    }
    setpgid(pid, pid);
    close(outpipe[1]); close(errpipe[1]);
    fcntl(outpipe[0], F_SETFL, O_NONBLOCK); fcntl(errpipe[0], F_SETFL, O_NONBLOCK);
    ProcessResult result;
    bool done = false; int status = 0;
    while (!done || outpipe[0] >= 0 || errpipe[0] >= 0) {
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        if (elapsed >= timeout && !result.timed_out) {
            result.timed_out = true;
            kill(-pid, SIGKILL);
        }
        for (int* fd : {&outpipe[0], &errpipe[0]}) {
            if (*fd < 0) continue;
            char buffer[8192];
            // Bound each drain so a producer cannot starve timeout checks.
            for (int batch = 0; batch < 32; ++batch) {
                ssize_t n = read(*fd, buffer, sizeof(buffer));
                if (n > 0) append_output(fd == &outpipe[0] ? result.out : result.err, buffer, static_cast<size_t>(n), result);
                else {
                    if (n == 0 || (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR)) { close(*fd); *fd = -1; }
                    break;
                }
            }
        }
        if (!done) {
            pid_t waited = waitpid(pid, &status, WNOHANG);
            done = waited == pid;
            if (done) result.elapsed_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        }
        if (result.timed_out && done) {
            for (int* fd : {&outpipe[0], &errpipe[0]}) if (*fd >= 0) { close(*fd); *fd = -1; }
        }
        if (!done || outpipe[0] >= 0 || errpipe[0] >= 0) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    result.exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    return result;
}
}
#endif

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
namespace corelens {
static std::string quote_windows(const std::string& arg) {
    std::string result = "\""; size_t slashes = 0;
    for (char c : arg) {
        if (c == '\\') { ++slashes; continue; }
        if (c == '"') result.append(slashes * 2 + 1, '\\');
        else result.append(slashes, '\\');
        slashes = 0; result += c;
    }
    result.append(slashes * 2, '\\'); result += '"'; return result;
}
ProcessResult run_process(const std::vector<std::string>& args, double timeout) {
    if (args.empty() || timeout <= 0) throw std::invalid_argument("command and positive timeout required");
    std::string command;
    for (const auto& arg : args) { if (!command.empty()) command += ' '; command += quote_windows(arg); }
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    HANDLE out_read = nullptr, out_write = nullptr, err_read = nullptr, err_write = nullptr;
    HANDLE job = CreateJobObjectA(nullptr, nullptr);
    auto cleanup = [&] {
        for (HANDLE h : {out_read, out_write, err_read, err_write, job}) if (h) CloseHandle(h);
    };
    if (!job || !CreatePipe(&out_read, &out_write, &security, 0) || !CreatePipe(&err_read, &err_write, &security, 0)) {
        cleanup(); throw std::runtime_error("could not create process resources");
    }
    SetHandleInformation(out_read, HANDLE_FLAG_INHERIT, 0);
    SetHandleInformation(err_read, HANDLE_FLAG_INHERIT, 0);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits));
    STARTUPINFOA startup{}; startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdOutput = out_write; startup.hStdError = err_write; startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    PROCESS_INFORMATION process{};
    auto start = std::chrono::steady_clock::now();
    if (!CreateProcessA(nullptr, command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr, nullptr, &startup, &process)) {
        auto error = GetLastError(); cleanup();
        throw std::runtime_error("CreateProcess failed with code " + std::to_string(error));
    }
    if (!AssignProcessToJobObject(job, process.hProcess)) {
        TerminateProcess(process.hProcess, 127); CloseHandle(process.hThread); CloseHandle(process.hProcess); cleanup();
        throw std::runtime_error("could not assign workload to process job");
    }
    ResumeThread(process.hThread); CloseHandle(process.hThread);
    CloseHandle(out_write); out_write = nullptr; CloseHandle(err_write); err_write = nullptr;
    ProcessResult result;
    for (;;) {
        for (HANDLE h : {out_read, err_read}) {
            for (int batch = 0; batch < 32; ++batch) {
                DWORD available = 0, count = 0;
                if (!PeekNamedPipe(h, nullptr, 0, nullptr, &available, nullptr) || !available) break;
                char buffer[8192];
                if (!ReadFile(h, buffer, available < sizeof(buffer) ? available : sizeof(buffer), &count, nullptr)) break;
                append_output(h == out_read ? result.out : result.err, buffer, count, result);
            }
        }
        if (WaitForSingleObject(process.hProcess, 1) == WAIT_OBJECT_0) break;
        if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() >= timeout) {
            result.timed_out = true; TerminateJobObject(job, 124); WaitForSingleObject(process.hProcess, INFINITE); break;
        }
    }
    result.elapsed_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    DWORD exit_code; GetExitCodeProcess(process.hProcess, &exit_code); result.exit_code = static_cast<int>(exit_code);
    // Drain output written just before exit.
    for (HANDLE h : {out_read, err_read}) {
        DWORD available = 0, count = 0; char buffer[8192];
        while (PeekNamedPipe(h, nullptr, 0, nullptr, &available, nullptr) && available && ReadFile(h, buffer, available < sizeof(buffer) ? available : sizeof(buffer), &count, nullptr))
            append_output(h == out_read ? result.out : result.err, buffer, count, result);
    }
    CloseHandle(process.hProcess); cleanup(); return result;
}
}
#endif
