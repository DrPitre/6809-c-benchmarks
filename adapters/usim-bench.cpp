// Bare-metal benchmark machine using the unmodified markrvmurray/usim CPU.
// Preserve the historical $FF00 console and SYNC-with-D exit conventions.
#include "mc6809.h"
#include "memory.h"
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>

static unsigned long long number(const char *text, int base,
                                 unsigned long long maximum)
{
    char *end;
    errno = 0;
    if (!text || !*text || *text == '-')
        throw std::runtime_error("missing or invalid numeric value");
    auto value = std::strtoull(text, &end, base);
    if (errno || *end || value > maximum)
        throw std::runtime_error("numeric value out of range");
    return value;
}

class Console : public MappedDevice {
public:
    Byte read(Word) override { return 0; }
    void write(Word, Byte value) override {
        std::putchar(value == '\r' ? '\n' : value);
    }
};

class BenchmarkCPU : public mc6809 {
    bool measuring = false, counting = false;
    Word begin = 0, end = 0;
    unsigned long long instructions = 0, windows = 0;
public:
    bool done = false;
    int result = 1;
    BenchmarkCPU() {
        const char *first = std::getenv("USIM_BENCH_BEGIN");
        const char *last = std::getenv("USIM_BENCH_END");
        if (bool(first) != bool(last))
            throw std::runtime_error("both measurement boundaries are required");
        if (first) {
            begin = number(first, 16, 65535);
            end = number(last, 16, 65535);
            if (begin == end)
                throw std::runtime_error("measurement boundaries must differ");
            measuring = true;
        }
        abort = [] { throw std::runtime_error("invalid CPU instruction"); };
    }
    void finish() const {
        if (measuring && (counting || windows == 0))
            throw std::runtime_error("incomplete instruction measurement");
    }
protected:
    void pre_exec() override {
        if (measuring && pc == end && counting) {
            std::fprintf(stderr, "BENCH_INSTRUCTIONS %llu\n", instructions);
            counting = false;
            ++windows;
        }
        if (measuring && pc == begin) {
            if (counting)
                throw std::runtime_error("nested measurement window");
            instructions = 0;
            counting = true;
        }
        if (counting)
            ++instructions;
    }
    void post_exec() override {
        if (waiting_sync) {
            result = d == 0 ? 0 : 1;
            done = true;
            halt();
        }
    }
};

static unsigned hexbyte(const std::string& line, size_t offset)
{
    unsigned value = 0;
    for (size_t i = offset; i < offset + 2; ++i) {
        char c = line.at(i);
        unsigned digit;
        if (c >= '0' && c <= '9') digit = c - '0';
        else if (c >= 'a' && c <= 'f') digit = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') digit = c - 'A' + 10;
        else throw std::runtime_error("invalid S-record hex digit");
        value = (value << 4) | digit;
    }
    return value;
}

// Validate and load the suite's 16-bit S-records, including their entry point.
static Word load(RAM& ram, const char *filename)
{
    std::ifstream file(filename);
    if (!file) throw std::runtime_error("cannot open S-record file");
    std::string line;
    bool data = false;
    while (std::getline(file, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        if (line.size() < 10 || line[0] != 'S')
            throw std::runtime_error("invalid S-record header");
        unsigned count = hexbyte(line, 2), sum = count;
        if (count < 3 || line.size() != 4 + 2 * count)
            throw std::runtime_error("invalid S-record length");
        for (size_t i = 4; i < line.size(); i += 2) sum += hexbyte(line, i);
        if ((sum & 255) != 255)
            throw std::runtime_error("invalid S-record checksum");
        unsigned address = (hexbyte(line, 4) << 8) | hexbyte(line, 6);
        if (line[1] == '1') {
            if (address + count - 3 > 65536)
                throw std::runtime_error("S-record exceeds 16-bit memory");
            for (unsigned i = 0; i < count - 3; ++i)
                ram.write(address + i, hexbyte(line, 8 + 2 * i));
            data = true;
        } else if (line[1] == '9') {
            if (!data || count != 3)
                throw std::runtime_error("invalid S-record entry point");
            return address;
        } else if (line[1] != '0' && line[1] != '5') {
            throw std::runtime_error("unsupported S-record type");
        }
    }
    throw std::runtime_error("missing S-record entry point");
}

int main(int argc, char **argv)
{
    try {
        if (argc == 2 && std::string(argv[1]) == "--version") {
            std::puts("markrvmurray/usim " USIM_REVISION " (benchmark adapter)");
            return 0;
        }
        if (argc != 2) throw std::runtime_error("usage: usim <srecfile>");
        BenchmarkCPU cpu;
        auto ram = std::make_shared<RAM>(65536);
        auto console = std::make_shared<Console>();
        cpu.attach_range(console, 0xff00, 1);
        cpu.attach(ram, 0, 0);
        Word entry = load(*ram, argv[1]);
        cpu.reset();
        cpu.set_pc(entry);
        const char *limit = std::getenv("USIM_MAX_INSTRUCTIONS");
        auto maximum = limit ? number(limit, 10, std::numeric_limits<unsigned long long>::max())
                             : 100000000ULL;
        for (unsigned long long i = 0; i < maximum && !cpu.done; ++i) cpu.tick();
        if (!cpu.done) throw std::runtime_error("instruction limit exceeded");
        cpu.finish();
        return cpu.result;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "usim: %s\n", error.what());
        return 1;
    }
}
