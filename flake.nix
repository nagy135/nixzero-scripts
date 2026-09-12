{
  description = "Python hardware experiments for nixzero";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {nixpkgs, ...}: let
    pkgs = nixpkgs.legacyPackages.aarch64-linux;
    python = pkgs.python3.withPackages (p: [p.lgpio]);
  in {
    packages.aarch64-linux.default = pkgs.writeShellApplication {
      name = "nixzero-servo";
      runtimeInputs = [python];
      text = ''exec python3 ${./servo.py} "$@"'';
    };
    devShells.aarch64-linux.default = pkgs.mkShell {packages = [python];};
  };
}
