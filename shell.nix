# Toolchains to build the pinned runtimes and run the harnesses on NixOS.
# gcc 13 matches CI (ubuntu-24.04): gcc 14 turns the implicit declarations
# of matiec's call wrappers into errors (notes/comparison.md, matiec item 13).
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell.override { stdenv = pkgs.gcc13Stdenv; } {
  packages = with pkgs; [
    gnumake pkg-config which
    flex bison autoconf automake libtool   # matiec, OpenPLC's matiec fork
    nodejs_22                              # STruC++
    rustup                                 # IronPLC, rk (rust-toolchain.toml pins 1.97.1)
    python3 git curl
    xvfb-run                               # 4diac IDE export
  ];
  shellHook = ''
    export LC_ALL=C.UTF-8
    export PATH=$HOME/.cargo/bin:$PATH
    rustup toolchain list | grep -q stable || rustup -q default stable
  '';
}
