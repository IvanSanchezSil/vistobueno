{
  description = "Validador de formato de tesis - entorno de desarrollo";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        pythonEnv = pkgs.python314.withPackages (ps: with ps; [
          fastapi
          uvicorn
          pydantic
          pyyaml
          python-docx
          pymupdf
          lxml
          pytest
          httpx
        ]);

        tesseractSpa = pkgs.tesseract.override {
          enableLanguages = [ "spa" "eng" ];
        };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.ocrmypdf
            tesseractSpa
            pkgs.poppler_utils
          ];

          shellHook = ''
            echo "Entorno listo: Python $(python3 --version)"
            echo "FastAPI, python-docx, PyMuPDF, pyyaml disponibles."
            echo "OCR: ocrmypdf, tesseract (spa+eng), pdftotext disponibles."
          '';
        };
      });
}
