#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    uint64_t n = argc > 1 ? strtoull(argv[1], NULL, 10) : 10000000;
    if (!n || n > 1000000000) return 2;
    uint64_t sum = 0;
    for (uint64_t i = 0; i < n; ++i) sum += (i * 17) ^ (i >> 3);
    printf("%" PRIu64 "\n", sum);
    return 0;
}
