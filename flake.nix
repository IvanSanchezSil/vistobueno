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
          email-validator
          aiosmtpd
          pyyaml
          python-docx
          pymupdf
          pytesseract
          pillow
          lxml
          pytest
          httpx
          python-multipart
          pytest-cov
          coverage
          markdown
          weasyprint
        ]);

        pythonTooling = pkgs.buildEnv {
          name = "vistobueno-python-tooling";
          paths = [ pkgs.ruff pkgs.mypy pkgs.pre-commit ];
        };

        tesseractSpa = pkgs.tesseract.override {
          enableLanguages = [ "spa" "eng" ];
        };
      in
      {
        # Entorno de desarrollo
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pythonTooling
            pkgs.ocrmypdf
            tesseractSpa
            pkgs.poppler-utils
          ];

          shellHook = ''
            echo "=== VistoBueno — entorno de desarrollo ==="
            echo "Python: $(python3 --version)"
            echo ""
            echo "Comandos disponibles:"
            echo "  nix run .#test -- tests/ -v                    # ejecutar tests"
            echo "  nix run .#serve -- validator.api:app --reload  # iniciar API"
            echo "  nix run .#smtp-dev                              # sink SMTP local (127.0.0.1:8025)"
            echo "  nix run .#test-local                            # e2e local: API + sink SMTP"
            echo "  nix flake check                                # tests + verificación"
            echo "  ruff check validator/ scripts/ tests/          # lint Python"
            echo "  mypy validator/ scripts/                       # tipos Python"
            echo "  python3 scripts/generate_openapi.py            # regenerar OpenAPI spec"
            echo "  python3 scripts/eval_contra_plantillas.py recursos/  # evaluar batch"
            echo ""
          '';
        };

        # Aplicaciones ejecutables con nix run
        apps = {
          default = self.apps.${system}.test;

          test = {
            type = "app";
            program = "${pythonEnv}/bin/pytest";
          };

          serve = {
            type = "app";
            program = "${pythonEnv}/bin/uvicorn";
          };

          # Sink SMTP local (aiosmtpd) para probar notificaciones sin
          # credenciales reales: acepta SMTP plano en 127.0.0.1:8025.
          smtp-dev = {
            type = "app";
            program = toString (pkgs.writeShellScript "smtp-dev" ''
              exec ${pythonEnv}/bin/aiosmtpd -n -l 127.0.0.1:8025
            '');
          };

          # Prueba local end-to-end: levanta la API + el sink SMTP y valida
          # el flujo de notificación. Ejecutar desde la raíz del repo.
          test-local = {
            type = "app";
            program = toString (pkgs.writeShellScript "test-local" ''
              if [ ! -f "$PWD/scripts/servidor_pruebas.py" ]; then
                echo "Error: ejecutar desde la raíz del repositorio (nix run .#test-local)"
                exit 1
              fi
              exec ${pythonEnv}/bin/python3 "$PWD/scripts/servidor_pruebas.py" "$@"
            '');
          };
        };

        # Verificaciones: pytest via nix flake check
        checks = {
          default = pkgs.runCommand "vistobueno-tests" {
            buildInputs = [ pythonEnv pythonTooling ];
          } ''
            cp -r ${self}/* .
            pytest tests/ -v --cov=validator --cov-report=term
            ruff check validator/ scripts/ tests/
            mypy validator/ scripts/
            touch $out
          '';
        };
      });
}
