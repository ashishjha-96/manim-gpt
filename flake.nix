{
  description = "Manim GPT - AI-Powered Video Generation API";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Define all required packages
        buildInputs = with pkgs; [
          # Python and package manager
          python314
          uv

          # Build tools
          gcc
          pkg-config
          meson
          ninja

          # Graphics libraries for pycairo and manim
          cairo
          cairo.dev
          pango
          pango.dev
          glib
          glib.dev
          harfbuzz
          harfbuzz.dev
          fontconfig
          fontconfig.dev
          freetype
          freetype.dev

          # X11 libraries
          xorg.libxcb
          xorg.xcbutil
          xorg.libX11
          xorg.xorgproto

          # Video processing
          ffmpeg

          # PostScript/PDF processing
          ghostscript

          # LaTeX for Manim text rendering
          (texlive.combine {
            inherit (texlive)
              scheme-basic
              standalone
              preview
              doublestroke
              relsize
              fundus-calligra
              wasysym
              physics
              dvisvgm
              rsfs
              wasy
              cm-super
              amsmath
              amsfonts;
          })

          # Node.js for React frontend
          nodejs_20
          nodePackages.npm
        ];

        # Environment variables for building
        shellEnv = {
          PKG_CONFIG_PATH = "${pkgs.cairo.dev}/lib/pkgconfig:${pkgs.pango.dev}/lib/pkgconfig:${pkgs.glib.dev}/lib/pkgconfig:${pkgs.harfbuzz.dev}/lib/pkgconfig:${pkgs.fontconfig.dev}/lib/pkgconfig:${pkgs.freetype.dev}/lib/pkgconfig:${pkgs.xorg.libxcb.dev}/lib/pkgconfig:${pkgs.xorg.libX11.dev}/lib/pkgconfig";
          CFLAGS = "-I${pkgs.fontconfig.dev}/include -I${pkgs.freetype.dev}/include/freetype2 -I${pkgs.xorg.libxcb.dev}/include -I${pkgs.xorg.libX11.dev}/include -I${pkgs.xorg.xorgproto}/include";
          LDFLAGS = "-L${pkgs.fontconfig.dev}/lib -L${pkgs.freetype.dev}/lib -L${pkgs.xorg.libxcb}/lib -L${pkgs.xorg.libX11}/lib";
          PYTHONUNBUFFERED = "1";
        };

      in
      {
        # Development shell
        devShells.default = pkgs.mkShell {
          inherit buildInputs;

          shellHook = ''
            echo "🎬 Manim GPT Development Environment"
            echo "===================================="
            echo "Python: $(python --version)"
            echo "UV: $(uv --version)"
            echo "FFmpeg: $(ffmpeg -version | head -n1)"
            echo "Node: $(node --version)"
            echo ""
            echo "Quick Start:"
            echo "  1. uv sync                    # Install Python dependencies"
            echo "  2. cp .env.example .env       # Set up environment variables"
            echo "  3. uvicorn main:app --reload  # Start FastAPI backend"
            echo "  4. uv run gradio_app.py       # Start Gradio UI (in new terminal)"
            echo ""

            # Set environment variables
            export PKG_CONFIG_PATH="${shellEnv.PKG_CONFIG_PATH}"
            export CFLAGS="${shellEnv.CFLAGS}"
            export LDFLAGS="${shellEnv.LDFLAGS}"
            export PYTHONUNBUFFERED="${shellEnv.PYTHONUNBUFFERED}"
          '';
        };

        # Package definition for manim-gpt
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "manim-gpt";
          version = "0.1.0";

          src = ./.;

          inherit buildInputs;

          nativeBuildInputs = with pkgs; [
            uv
            nodejs_20
          ];

          buildPhase = ''
            export HOME=$TMPDIR
            export PKG_CONFIG_PATH="${shellEnv.PKG_CONFIG_PATH}"
            export CFLAGS="${shellEnv.CFLAGS}"
            export LDFLAGS="${shellEnv.LDFLAGS}"

            # Install Python dependencies
            uv sync --frozen

            # Build frontend
            cd frontend
            npm ci
            npm run build
            cd ..
          '';

          installPhase = ''
            mkdir -p $out/bin $out/lib

            # Copy application files
            cp -r . $out/lib/manim-gpt

            # Create wrapper script
            cat > $out/bin/manim-gpt << EOF
            #!${pkgs.bash}/bin/bash
            cd $out/lib/manim-gpt
            exec ${pkgs.uv}/bin/uv run uvicorn main:app --host 0.0.0.0 --port 8000
            EOF

            chmod +x $out/bin/manim-gpt
          '';

          meta = with pkgs.lib; {
            description = "AI-Powered Manim Video Generation API";
            homepage = "https://github.com/yourusername/manim-gpt";
            license = licenses.mit;
            platforms = platforms.unix;
          };
        };

        # Docker image using Nix
        packages.dockerImage = pkgs.dockerTools.buildLayeredImage {
          name = "manim-gpt";
          tag = "latest";

          contents = [
            self.packages.${system}.default
            pkgs.bash
            pkgs.coreutils
            pkgs.curl
          ] ++ buildInputs;

          config = {
            Cmd = [ "${self.packages.${system}.default}/bin/manim-gpt" ];
            ExposedPorts = {
              "8000/tcp" = {};
              "7860/tcp" = {};
            };
            Env = [
              "PYTHONUNBUFFERED=1"
              "PKG_CONFIG_PATH=${shellEnv.PKG_CONFIG_PATH}"
            ];
            WorkingDir = "/app";
            Healthcheck = {
              Test = [ "CMD" "curl" "-f" "http://localhost:8000/health" ];
              Interval = 30000000000;  # 30s in nanoseconds
              Timeout = 10000000000;   # 10s
              StartPeriod = 40000000000; # 40s
              Retries = 3;
            };
          };
        };

        # Formatter
        formatter = pkgs.nixpkgs-fmt;
      }
    );
}
