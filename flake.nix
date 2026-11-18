{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.wiki = {
    url = "git+https://github.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation.wiki.git";
    flake = false;
  };

  outputs =
    {
      self,
      nixpkgs,
      wiki,
      ...
    }:
    let
      forSystems =
        f:
        nixpkgs.lib.genAttrs nixpkgs.lib.systems.flakeExposed (
          system: f (import nixpkgs { inherit system; })
        );
    in
    {
      formatter = forSystems (
        pkgs:
        pkgs.treefmt.withConfig {
          runtimeInputs = with pkgs; [
            git
            nixfmt
            ruff
            oxfmt
          ];
          settings = {
            tree-root-file = "flake.nix";
            walk = "git";
            formatter = {
              nix = {
                command = "nixfmt";
                includes = [ "*.nix" ];
              };
              python = {
                command = "ruff";
                options = [ "format" ];
                includes = [ "*.py" ];
              };
              web = {
                command = "oxfmt";
                options = [ "--write" ];
                includes = [
                  "*.css"
                  "*.html"
                  "*.js"
                  "*.json"
                  "*.md"
                  "*.yaml"
                  "*.yml"
                ];
              };
            };
          };
        }
      );

      packages = forSystems (pkgs: {
        default = pkgs.stdenvNoCC.mkDerivation {
          pname = "uad-ng-website";
          version = "0";
          dontUnpack = true;
          dontConfigure = true;

          nativeBuildInputs = with pkgs; [
            python3
            cmark-gfm
          ];

          buildPhase = ''
            python3 ${./build.py} ${wiki} ${./template.html} dist
          '';

          installPhase = ''
            mkdir -p "$out"
            cp -r dist/. "$out/"
            install -m 644 ${./assets/logo-dark.png} "$out/logo.png"
            install -m 644 ${./lupin.css} "$out/lupin.css"
            touch "$out/.nojekyll"
          '';
        };
      });

      apps = forSystems (pkgs: {
        default = {
          type = "app";
          program = "${pkgs.writeShellScript "serve" ''
            exec ${pkgs.lib.getExe pkgs.darkhttpd} ${
              self.packages.${pkgs.stdenv.hostPlatform.system}.default
            } --addr 127.0.0.1 --port 8080 --no-listing
          ''}";
        };
      });
    };
}
