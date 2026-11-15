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
      formatter = forSystems (pkgs: pkgs.nixfmt-tree);

      packages = forSystems (pkgs: {
        default = pkgs.stdenvNoCC.mkDerivation {
          pname = "uad-ng-website";
          version = "0";

          src = pkgs.lib.cleanSource ./.;

          nativeBuildInputs = with pkgs; [
            python3
            cmark-gfm
          ];

          buildPhase = ''
            runHook preBuild

            python3 build.py ${wiki} dist

            runHook postBuild
          '';

          installPhase = ''
            runHook preInstall

            mkdir -p $out
            cp -r dist/. $out/

            runHook postInstall
          '';
        };
      });

      apps = forSystems (pkgs: {
        default = {
          type = "app";
          program = "${pkgs.writeShellScript "serve" ''
            exec ${pkgs.python3}/bin/python3 -m http.server 8080 --directory ${
              self.packages.${pkgs.stdenv.hostPlatform.system}.default
            }
          ''}";
        };
      });
    };
}
