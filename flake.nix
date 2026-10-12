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
            # Node LTS: toolchain del frontend (npm ci && npm run build).
            # La versión queda fijada por flake.lock.
            pkgs.nodejs
          ];

          shellHook = ''
            echo "=== VistoBueno — entorno de desarrollo ==="
            echo "Python: $(python3 --version)"
            echo ""
            echo "Comandos disponibles:"
            echo "  nix run .#test -- tests/ -v                    # ejecutar tests"
            echo "  nix run .#serve -- validator.api:app --reload  # iniciar API"
            echo "  nix run .#smtp-dev                              # sink SMTP local (127.0.0.1:8025)"
            echo "  nix run .#test-local                            # e2e local: build + suite + flujo completo"
            echo "  nix flake check                                # tests + verificación"
            echo "  ruff check validator/ scripts/ tests/          # lint Python"
            echo "  mypy validator/ scripts/                       # tipos Python"
            echo "  cd frontend && npm ci && npm run build         # build del frontend"
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

          # Prueba end-to-end local (Semana 7): build del frontend, suite
          # backend, servicios en :8000/:5173 y 9 checks del flujo completo
          # (incluida la notificación). Requiere puertos libres y npm ci
          # hecho en frontend/. Ver scripts/e2e_flujo_completo.sh.
          # (Hallazgo C3: antes apuntaba a scripts/servidor_pruebas.py,
          # que no existe — el comando anunciado daba error.)
          test-local = {
            type = "app";
            program = toString (pkgs.writeShellScript "test-local" ''
              if [ ! -f "$PWD/scripts/e2e_flujo_completo.sh" ]; then
                echo "Error: ejecutar desde la raíz del repositorio (nix run .#test-local)"
                exit 1
              fi
              exec ${pkgs.bash}/bin/bash "$PWD/scripts/e2e_flujo_completo.sh" "$@"
            '');
          };
        };

        # Verificaciones: cada una corre aislada para que un fallo no
        # oculte el estado de las demás (hallazgo C7: antes, si pytest
        # fallaba, ruff y mypy ni corrían y no se veía qué más estaba mal).
        checks = {
          tests = pkgs.runCommand "vistobueno-tests" {
            buildInputs = [ pythonEnv ];
          } ''
            cp -r ${self}/* .
            pytest tests/ -v --cov=validator --cov-report=term
            touch $out
          '';

          ruff = pkgs.runCommand "vistobueno-ruff" {
            buildInputs = [ pythonTooling ];
          } ''
            cp -r ${self}/* .
            ruff check validator/ scripts/ tests/
            touch $out
          '';

          mypy = pkgs.runCommand "vistobueno-mypy" {
            buildInputs = [ pythonEnv pythonTooling ];
          } ''
            cp -r ${self}/* .
            mypy validator/ scripts/
            touch $out
          '';
        };
      });
}
