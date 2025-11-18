# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-25.05"; # or "unstable"
  # Use https://search.nixos.org/packages to find packages
  packages = [
    # pkgs.go
    pkgs.python314
    pkgs.uv
    # Build dependencies for pycairo and manim
    pkgs.gcc
    pkgs.cairo
    pkgs.cairo.dev
    pkgs.pkg-config
    pkgs.meson
    pkgs.ninja
    pkgs.ffmpeg
    pkgs.pango
    pkgs.pango.dev
    pkgs.glib
    pkgs.glib.dev
    pkgs.harfbuzz
    pkgs.harfbuzz.dev
    pkgs.fontconfig
    pkgs.fontconfig.dev
    pkgs.freetype
    pkgs.freetype.dev
    pkgs.xorg.libxcb
    pkgs.xorg.xcbutil
    pkgs.xorg.libX11
    pkgs.xorg.xorgproto
    # LaTeX for Manim text rendering
    # Full TeX Live distribution with all packages Manim needs
    (pkgs.texlive.combine {
      inherit (pkgs.texlive) scheme-basic standalone preview doublestroke relsize fundus-calligra wasysym physics dvisvgm rsfs wasy cm-super amsmath amsfonts;
    })
    # used for PostScript/PDF processing
    pkgs.ghostscript
    # Node.js for React frontend
    pkgs.nodejs_20
    pkgs.nodePackages.npm
  ];
  # Sets environment variables in the workspace
  env = {
    PKG_CONFIG_PATH = "${pkgs.cairo.dev}/lib/pkgconfig:${pkgs.pango.dev}/lib/pkgconfig:${pkgs.glib.dev}/lib/pkgconfig:${pkgs.harfbuzz.dev}/lib/pkgconfig:${pkgs.fontconfig.dev}/lib/pkgconfig:${pkgs.freetype.dev}/lib/pkgconfig:${pkgs.xorg.libxcb.dev}/lib/pkgconfig:${pkgs.xorg.libX11.dev}/lib/pkgconfig";
    CFLAGS = "-I${pkgs.fontconfig.dev}/include -I${pkgs.freetype.dev}/include/freetype2 -I${pkgs.xorg.libxcb.dev}/include -I${pkgs.xorg.libX11.dev}/include -I${pkgs.xorg.xorgproto}/include";
    LDFLAGS = "-L${pkgs.fontconfig.dev}/lib -L${pkgs.freetype.dev}/lib -L${pkgs.xorg.libxcb}/lib -L${pkgs.xorg.libX11}/lib";
  };
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      # "vscodevim.vim"
      "google.gemini-cli-vscode-ide-companion"
      "ms-python.python"
    ];
    # Enable previews
    previews = {
      enable = true;
      previews = {
        # React + Tailwind frontend (default)
        web = {
          command = ["npm" "run" "dev" "--" "--host" "0.0.0.0" "--port" "$PORT"];
          manager = "web";
          cwd = "frontend";
          env = {
            VITE_API_URL = "http://localhost:8000";
          };
        };
        # Gradio UI (alternative)
        gradio = {
          command = ["uv" "run" "gradio_app.py"];
          manager = "web";
          env = {
            PORT = "$PORT";
            API_URL = "http://localhost:8000";
          };
        };
      };
    };
    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        # Install Python dependencies
        uv-sync = "uv sync";
        # Install React frontend dependencies
        npm-install = "cd frontend && npm install";
        # Open editors for the following files by default, if they exist:
        default.openFiles = [ "README.md" "frontend/src/App.jsx" ];
      };
      # Runs when the workspace is (re)started
      onStart = {
        # Start the FastAPI backend server
        start-api = "uv run uvicorn main:app --host 0.0.0.0 --port 8000 &";
      };
    };
  };
}
