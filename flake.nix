{
  description = "Python 100 Days of Code Environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    devShells.${system}.default = pkgs.mkShell {
      # 1. Updated dependencies using default python3
      buildInputs = with pkgs; [
        python3
        python3Packages.pip
        python3Packages.virtualenv
        black       
        ruff     
      ];

      # 2. Automate the local virtual environment creation
      shellHook = ''
        echo "Welcome to your Python Workspace."
        
        if [ ! -d .venv ]; then
          echo "Initializing isolated .venv..."
          python -m venv .venv
        fi
        
        source .venv/bin/activate
        
        echo "Environment Ready."
      '';
    };
  };
}
