#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -Wconversion -Werror main.cpp -o router
