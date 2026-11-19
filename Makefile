CC = cc
CFLAGS = -O2 -std=c89 -pedantic -Wall -Wextra
CPPFLAGS = -Iinclude
BENCHMARKS = crc16 insertion_sort mix16
BINARIES = $(addprefix build/host/,$(BENCHMARKS))

.PHONY: all check clean
all: $(BINARIES)

build/host:
	mkdir -p $@

build/host/runner.o: adapters/host.c include/bench.h | build/host
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

build/host/%.o: benchmarks/%.c include/bench.h | build/host
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

build/host/%: build/host/%.o build/host/runner.o
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

check: all
	python3 tools/check.py

clean:
	rm -rf build
